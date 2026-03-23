"""
台本と収集資料の差分分析ロジック
"""
from __future__ import annotations

import asyncio
import csv
import json
import math
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.adapters import ContentAdapterManager
from core.utils.logger import logger

from .research_models import AlignmentReport, ResearchPackage
from .research_models import SourceInfo

_SENTENCE_SPLIT_RE = re.compile(r"[。．.!?！？\n]+")
_TOKEN_RE = re.compile(r"[A-Za-z0-9一-龥ぁ-んァ-ヶー]{2,}")
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_STOP_WORDS = {
    "こと",
    "これ",
    "それ",
    "ため",
    "よう",
    "もの",
    "です",
    "ます",
    "した",
    "して",
    "いる",
    "ある",
    "なる",
    "する",
    "the",
    "and",
    "for",
    "with",
}


class ScriptAlignmentAnalyzer:
    """ResearchPackage と台本の整合性を分析する。"""

    def __init__(self) -> None:
        self._adapter_manager = ContentAdapterManager()

    async def load_script(self, script_path: Path) -> Dict[str, Any]:
        """TXT / CSV / JSON を内部スキーマへ正規化する。"""
        suffix = script_path.suffix.lower()
        if suffix == ".json":
            with open(script_path, "r", encoding="utf-8") as handle:
                raw_script = json.load(handle)
            normalized = await self._adapter_manager.normalize_script(raw_script)
            return self._normalize_segments(normalized)

        if suffix == ".txt":
            text = script_path.read_text(encoding="utf-8")
            return self._normalize_text_script(text, title=script_path.stem)

        if suffix == ".csv":
            return self._load_csv_script(script_path)

        raise ValueError(f"未対応のスクリプト形式です: {script_path}")

    async def analyze(
        self,
        package: ResearchPackage,
        normalized_script: Dict[str, Any],
    ) -> AlignmentReport:
        """台本と資料の差分を分析し、AlignmentReport を返す。"""
        source_candidates = self._build_source_candidates(package.sources)
        analysis: List[Dict[str, Any]] = []
        matched_claim_keys: set[str] = set()

        for segment in normalized_script.get("segments", []):
            segment_index = int(segment.get("index", 0) or 0)
            segment_text = str(segment.get("text", "")).strip()
            segment_speaker = segment.get("speaker", "")
            claims = self.extract_claims(segment_text, segment.get("key_points"))

            if not claims:
                analysis.append(
                    {
                        "segment_index": segment_index,
                        "text": segment_text,
                        "speaker": segment_speaker,
                        "status": "orphaned",
                        "matched_source": None,
                        "matched_claim": None,
                        "suggestion": "主張を抽出できませんでした。文を具体化してください。",
                    }
                )
                continue

            claim_matches: List[Dict[str, Any]] = []
            for claim in claims:
                match = self._match_claim(claim, source_candidates)
                if match is not None:
                    claim_matches.append(match)

            if not claim_matches:
                analysis.append(
                    {
                        "segment_index": segment_index,
                        "text": segment_text,
                        "speaker": segment_speaker,
                        "status": "orphaned",
                        "matched_source": None,
                        "matched_claim": None,
                        "suggestion": "出典不明です。根拠を追加するか、文を削除してください。",
                    }
                )
                continue

            best_match = max(claim_matches, key=lambda item: item["score"])
            status = "supported"
            suggestion = None

            if any(match["conflict"] for match in claim_matches):
                status = "conflict"
                suggestion = "数値または主張が資料と一致しません。出典側の値を確認してください。"

            required_matches = max(1, math.ceil(len(claims) / 2))
            if len(claim_matches) < required_matches and status != "conflict":
                status = "orphaned"
                suggestion = "一部の主張に根拠が不足しています。出典を追加してください。"

            for match in claim_matches:
                matched_claim_keys.add(match["claim_key"])

            analysis.append(
                {
                    "segment_index": segment_index,
                    "text": segment_text,
                    "speaker": segment_speaker,
                    "status": status,
                    "matched_source": best_match["url"],
                    "matched_claim": best_match["claim"],
                    "suggestion": suggestion,
                }
            )

        # ------------------------------------------------------------------
        # 追加: exact/token matchで orphaned となったものを LLM 翻訳・意味照合で救う
        # ------------------------------------------------------------------
        orphaned_items = [
            item for item in analysis
            if item.get("status") == "orphaned" and item.get("segment_index") is not None
        ]
        if orphaned_items and source_candidates:
            await self._async_llm_alignment(orphaned_items, source_candidates)
            # 再評価された item の claim_key を matched_claim_keys に追加
            for item in analysis:
                if item.get("status") == "supported" and "claim_key_used" in item:
                    matched_claim_keys.add(item["claim_key_used"])
                    item.pop("claim_key_used", None)

        for source in package.sources:
            for claim in self._get_candidate_claims(source):
                claim_key = self._make_claim_key(source.url, claim)
                if claim_key in matched_claim_keys:
                    continue
                if not source.key_claims:
                    continue
                analysis.append(
                    {
                        "segment_index": None,
                        "text": None,
                        "status": "missing",
                        "matched_source": source.url,
                        "matched_claim": claim,
                        "suggestion": "資料にある重要事項です。台本への追加を検討してください。",
                    }
                )

        summary = self._build_summary(analysis)
        package_id = package.package_id
        report_id = f"ar_{package_id}"
        return AlignmentReport(
            report_id=report_id,
            package_id=package_id,
            analysis=analysis,
            summary=summary,
        )

    def save_report(self, report: AlignmentReport, output_dir: Path) -> Path:
        """AlignmentReport を JSON 保存する。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "alignment_report.json"
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)
        logger.info(f"AlignmentReport を保存しました: {report_path}")
        return report_path

    def export_to_csv(self, analysis: List[Dict[str, Any]], output_path: Path) -> Path:
        """分析結果（採否反映後）を標準制作CSV形式で出力する。"""
        rows = []
        for item in analysis:
            # adopted または supported かつ segment_index があるもののみ出力
            status = item.get("status")
            if status in ("supported", "adopted") and item.get("segment_index") is not None:
                speaker = item.get("speaker", "ナレーター") or "ナレーター"
                text = item.get("text", "")
                rows.append([speaker, text])

        with open(output_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)

        logger.info(f"最終CSVをエクスポートしました: {output_path}")
        return output_path

    async def _async_llm_alignment(
        self,
        orphaned_items: List[Dict[str, Any]],
        candidates: Sequence[Dict[str, Any]],
    ) -> None:
        """Use LLM to perform semantic matching for orphaned sentences."""
        try:
            from core.llm_provider import create_llm_provider
            import json
            provider = create_llm_provider()

            sentences_payload = []
            for item in orphaned_items:
                # プロンプト圧縮: 全文ではなく先頭150文字 + key_points を送る
                full_text = item.get("text", "")
                truncated = full_text[:150] + ("..." if len(full_text) > 150 else "")
                sentences_payload.append({
                    "id": item["segment_index"],
                    "text": truncated,
                })

            claims_payload = []
            for c in candidates:
                claims_payload.append({
                    "claim_key": c["claim_key"],
                    "text": c["claim"]
                })

            prompt = f"""
You are an expert multi-lingual analyst.
Match the following Japanese sentences to the English key claims that support them.
A sentence is supported if its factual claims are present in the key claim.
Output valid JSON only.

Input Sentences (Japanese):
{json.dumps(sentences_payload, ensure_ascii=False, indent=2)}

Candidate Claims (English):
{json.dumps(claims_payload, ensure_ascii=False, indent=2)}

Format:
{{
  "matches": [
    {{
      "sentence_id": <id>,
      "matched_claim_keys": ["<claim_key_1>", "<claim_key_2>"]
    }}
  ]
}}
Only output the JSON. Do not include markdown formatting or tags like ```json.
"""
            content_str = await provider.generate_text(prompt)
            content_str = content_str.strip()

            if content_str.startswith("```json"):
                content_str = content_str[7:]
            elif content_str.startswith("```"):
                content_str = content_str[3:]
            if content_str.endswith("```"):
                content_str = content_str[:-3]
            content_str = content_str.strip()

            result = json.loads(content_str)

            matches = result.get("matches", [])
            match_dict = {m["sentence_id"]: m.get("matched_claim_keys", []) for m in matches}

            for item in orphaned_items:
                seg_id = item["segment_index"]
                matched_keys = match_dict.get(seg_id, [])
                if matched_keys:
                    for claim_key in matched_keys:
                        for cand in candidates:
                            if cand["claim_key"] == claim_key:
                                item["status"] = "supported"
                                item["suggestion"] = None
                                item["matched_source"] = cand["url"]
                                item["matched_claim"] = cand["claim"]
                                item["claim_key_used"] = claim_key
                                break
                        if item["status"] == "supported":
                            break

        except Exception as e:
            logger.warning(f"LLM semantic alignment failed: {e}")

    def extract_claims(self, text: str, key_points: Optional[Sequence[str]] = None) -> List[str]:
        """文から claims を抽出する。"""
        claims: List[str] = []
        if key_points:
            claims.extend(self._clean_claim(point) for point in key_points if self._clean_claim(point))

        for chunk in _SENTENCE_SPLIT_RE.split(text):
            cleaned = self._clean_claim(chunk)
            if cleaned and cleaned not in claims:
                claims.append(cleaned)

        return claims

    def _build_source_candidates(self, sources: Sequence[SourceInfo]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for source in sources:
            for claim in self._get_candidate_claims(source):
                candidates.append(
                    {
                        "url": source.url,
                        "claim": claim,
                        "claim_key": self._make_claim_key(source.url, claim),
                        "tokens": self._tokenize(claim),
                        "numbers": set(_NUMBER_RE.findall(claim)),
                    }
                )
        return candidates

    def _get_candidate_claims(self, source: SourceInfo) -> List[str]:
        claims = [claim for claim in source.key_claims if self._clean_claim(claim)]
        if claims:
            return claims

        fallback_claims: List[str] = []
        for candidate in (source.title, source.content_preview):
            cleaned = self._clean_claim(candidate)
            if cleaned:
                fallback_claims.append(cleaned)
        return fallback_claims

    def _match_claim(
        self,
        claim: str,
        candidates: Sequence[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        claim_tokens = self._tokenize(claim)
        if not claim_tokens:
            return None

        claim_numbers = set(_NUMBER_RE.findall(claim))
        best_match: Optional[Dict[str, Any]] = None

        for candidate in candidates:
            score = self._score_claim_match(claim, claim_tokens, candidate)
            if score < 0.3:
                continue

            conflict = False
            if claim_numbers and candidate["numbers"] and (claim_numbers - candidate["numbers"]):
                conflict = True

            match = {
                "url": candidate["url"],
                "claim": candidate["claim"],
                "claim_key": candidate["claim_key"],
                "score": score,
                "conflict": conflict,
            }
            if best_match is None or float(match.get("score", 0.0)) > float(best_match.get("score", 0.0)):
                best_match = match

        return best_match

    def _score_claim_match(
        self,
        claim: str,
        claim_tokens: set[str],
        candidate: Dict[str, Any],
    ) -> float:
        candidate_claim = candidate["claim"]
        candidate_tokens = candidate["tokens"]
        if not candidate_tokens:
            return 0.0

        if claim in candidate_claim or candidate_claim in claim:
            return 1.0

        overlap = claim_tokens & candidate_tokens
        union = claim_tokens | candidate_tokens
        if not union:
            return 0.0

        token_score = len(overlap) / len(union)
        length_bonus = min(len(overlap) / max(len(claim_tokens), 1), 1.0)
        return (token_score * 0.7) + (length_bonus * 0.3)

    def _build_summary(self, analysis: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        statuses = ["supported", "orphaned", "missing", "conflict"]
        summary = {"total_segments": 0}
        summary["total_segments"] = sum(1 for item in analysis if item.get("segment_index") is not None)
        for status in statuses:
            summary[status] = sum(1 for item in analysis if item.get("status") == status)
        return summary

    def _normalize_text_script(self, text: str, title: str) -> Dict[str, Any]:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
        segments = []
        for index, paragraph in enumerate(paragraphs, start=1):
            segments.append(
                {
                    "index": index,
                    "speaker": "",
                    "text": paragraph,
                    "source_refs": [],
                    "confidence": "unverified",
                    "key_points": [],
                }
            )

        return {
            "title": title,
            "segments": segments,
        }

    def _load_csv_script(self, script_path: Path) -> Dict[str, Any]:
        segments = []
        with open(script_path, "r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            for index, row in enumerate(reader, start=1):
                if not row:
                    continue
                speaker = row[0].strip() if len(row) > 0 else ""
                text = row[1].strip() if len(row) > 1 else ""
                if not text:
                    continue
                segments.append(
                    {
                        "index": index,
                        "speaker": speaker,
                        "text": text,
                        "source_refs": [],
                        "confidence": "unverified",
                        "key_points": [],
                    }
                )

        return {"title": script_path.stem, "segments": segments}

    def _normalize_segments(self, script: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {"title": script.get("title", ""), "segments": []}
        for index, raw_segment in enumerate(script.get("segments", []), start=1):
            if hasattr(raw_segment, "__dataclass_fields__"):
                segment_data = asdict(raw_segment)
            elif hasattr(raw_segment, "__dict__") and not isinstance(raw_segment, dict):
                segment_data = dict(raw_segment.__dict__)
            else:
                segment_data = dict(raw_segment)

            text = (
                segment_data.get("text")
                or segment_data.get("content")
                or segment_data.get("body")
                or ""
            )
            normalized["segments"].append(
                {
                    "index": int(segment_data.get("index", index) or index),
                    "speaker": segment_data.get("speaker", ""),
                    "text": str(text).strip(),
                    "source_refs": segment_data.get("source_refs", []),
                    "confidence": segment_data.get("confidence", "unverified"),
                    "key_points": segment_data.get("key_points", []),
                }
            )
        return normalized

    def _clean_claim(self, text: str) -> str:
        cleaned = str(text).strip().strip("-").strip("・").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if len(cleaned) < 6:
            return ""
        return cleaned

    def _tokenize(self, text: str) -> set[str]:
        return {
            token.lower()
            for token in _TOKEN_RE.findall(text)
            if token.lower() not in _STOP_WORDS
        }

    def _make_claim_key(self, url: str, claim: str) -> str:
        return f"{url}::{claim}"
