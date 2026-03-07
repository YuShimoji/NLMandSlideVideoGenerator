# SofTalk Integration Technical Assessment

> **DEPRECATED (2026-03-04)**: SofTalk/AquesTalk/VOICEVOX統合はYMM4一本化方針により削除されました。本文書は歴史的参照として保持されています。現行の音声ワークフローは `docs/voice_path_comparison.md` を参照してください。

**Document Version**: 1.0
**Date**: 2026-03-02
**Status**: DEPRECATED (旧 TASK_014 Deliverable)
**Author**: Antigravity (Orchestrator)

---

## Executive Summary

This document provides a technical assessment of the SofTalk integration implemented in TASK_008, evaluates its current status, identifies limitations, and recommends potential improvements or alternative approaches for text-to-speech (TTS) functionality in the NLMandSlideVideoGenerator project.

**Key Findings:**
- ✅ **SofTalk integration is functional** and supports batch processing of CSV timelines
- ⚠️ **Environment dependency** limits portability (requires SofTalk installation)
- ⚠️ **Limited voice customization** compared to modern TTS solutions
- 🔄 **Alternative TTS engines** (VOICEVOX, Google TTS) offer better flexibility

---

## 1. Current Implementation Review

### 1.1 Implementation Location
- **Script**: `scripts/tts_batch_softalk_aquestalk.py`
- **Task Reference**: TASK_008_SofTalkIntegration.md (CLOSED)
- **Status**: Completed and operational

### 1.2 Core Functionality
The current implementation provides:

1. **CSV Timeline Processing**
   - Reads speaker and text data from CSV files
   - Generates sequential WAV files (001.wav, 002.wav, ...)
   - Skips already-generated files to avoid redundant processing

2. **SofTalk/AquesTalk Integration**
   - Supports both SofTalk and AquesTalk engines
   - Detects executables via environment variables (`SOFTALK_EXE`, `AQUESTALK_EXE`)
   - Provides fallback to default installation paths

3. **Error Handling**
   - Retry mechanism for transient failures
   - Comprehensive logging of success/skip/error counts
   - Dry-run mode for testing commands without execution

4. **Speaker-Voice Mapping**
   - JSON-based configuration for speaker-to-voice preset mapping
   - Supports engine-specific voice selection
   - Fallback to default voice when mapping is unavailable

### 1.3 Usage Example
```bash
# Generate audio files from CSV timeline
python scripts/tts_batch_softalk_aquestalk.py \
  --engine softalk \
  --csv samples/basic_dialogue/timeline.csv \
  --out-dir samples/basic_dialogue/audio

# Force regeneration of existing files
python scripts/tts_batch_softalk_aquestalk.py ... --no-skip

# Adjust retry count
python scripts/tts_batch_softalk_aquestalk.py ... --max-retries 5
```

---

## 2. Technical Evaluation

### 2.1 Strengths ✅

| Aspect | Evaluation |
|--------|-----------|
| **Batch Processing** | Excellent. Efficiently processes entire CSV timelines in one operation. |
| **File Management** | Good. Implements skip logic to avoid redundant regeneration. |
| **Error Resilience** | Good. Retry mechanism handles transient failures. |
| **Extensibility** | Good. Supports multiple TTS engines (SofTalk, AquesTalk) via abstraction. |
| **Integration** | Excellent. Seamlessly integrates with existing CSV pipeline workflow. |

### 2.2 Limitations ⚠️

| Aspect | Issue | Impact |
|--------|-------|--------|
| **Environment Dependency** | Requires SofTalk/AquesTalk installation on Windows | Limits portability to other platforms and CI/CD environments |
| **Voice Quality** | Limited to SofTalk's synthetic voices | Lower quality compared to modern neural TTS |
| **Customization** | Basic voice parameters (speed, volume) | Lacks prosody, emotion, and accent control |
| **Licensing** | SofTalk is free but AquesTalk may require licensing for commercial use | Potential legal/cost implications for production |
| **Real-time Performance** | Sequential processing can be slow for large timelines | No parallel processing support |

### 2.3 Compatibility Matrix

| Environment | SofTalk Support | Alternative Solutions |
|-------------|----------------|----------------------|
| Windows (Local) | ✅ Full | VOICEVOX, Coeiroink |
| Windows (CI/CD) | ❌ Requires installation | Cloud TTS APIs |
| Linux/macOS | ❌ Not supported | VOICEVOX (via Wine), Cloud APIs |
| Docker | ⚠️ Complex setup | Cloud TTS APIs recommended |

---

## 3. Alternative TTS Solutions

### 3.1 VOICEVOX (Recommended)

**Overview**: Open-source, high-quality Japanese TTS engine

**Pros:**
- ✅ Excellent voice quality (neural-based)
- ✅ Multiple voice characters and emotions
- ✅ HTTP API for easy integration
- ✅ Free for commercial use
- ✅ Cross-platform (Windows, Linux, macOS)
- ✅ Active development and community support

**Cons:**
- ⚠️ Requires local installation (or Docker container)
- ⚠️ Higher resource requirements (GPU recommended)
- ⚠️ API may change between versions

**Integration Effort**: **Medium** (1-2 days)
- HTTP API client implementation
- Speaker/style mapping configuration
- Error handling and retry logic
- Docker deployment for CI/CD

**Example Integration:**
```python
import requests

def generate_voicevox_audio(text: str, speaker_id: int, output_path: Path):
    # Step 1: Create audio query
    query_response = requests.post(
        f"http://localhost:50021/audio_query",
        params={"text": text, "speaker": speaker_id}
    )
    audio_query = query_response.json()

    # Step 2: Synthesize audio
    synthesis_response = requests.post(
        f"http://localhost:50021/synthesis",
        params={"speaker": speaker_id},
        json=audio_query
    )

    # Step 3: Save to file
    output_path.write_bytes(synthesis_response.content)
```

### 3.2 Cloud TTS APIs

**Options:**
- Google Cloud Text-to-Speech
- Amazon Polly
- Microsoft Azure Cognitive Services
- OpenAI TTS

**Pros:**
- ✅ No local installation required
- ✅ High-quality neural voices
- ✅ Multi-language support
- ✅ Scalable and reliable

**Cons:**
- ⚠️ Requires API key and internet connection
- ⚠️ Cost per character (can add up for large projects)
- ⚠️ Latency dependent on network
- ⚠️ Privacy concerns (text sent to cloud)

**Integration Effort**: **Low** (1 day)
- API client library integration
- Authentication setup
- Cost monitoring and rate limiting

### 3.3 Coeiroink

**Overview**: Japanese TTS with emotional control

**Pros:**
- ✅ Emotion and intonation control
- ✅ Similar API to VOICEVOX
- ✅ Good voice quality

**Cons:**
- ⚠️ Less mature than VOICEVOX
- ⚠️ Smaller community

**Integration Effort**: **Low** (similar to VOICEVOX)

---

## 4. Recommendations

### 4.1 Short-term (1-2 weeks)

**Keep SofTalk Integration**
- ✅ Current implementation is functional and meets immediate needs
- ✅ No breaking changes required
- ⚠️ Document limitations and setup requirements clearly

**Action Items:**
1. Update README with SofTalk installation instructions
2. Add troubleshooting guide for common issues (device detection, encoding)
3. Test on fresh Windows environment to validate setup process

### 4.2 Mid-term (1-2 months)

**Add VOICEVOX Support**
- ✅ Better voice quality improves final video output
- ✅ Provides alternative for users without SofTalk
- ✅ Can coexist with SofTalk (user choice)

**Implementation Plan:**
1. Create `scripts/tts_batch_voicevox.py` (separate from SofTalk script)
2. Add VOICEVOX detection to `src/core/utils/tool_detection.py`
3. Update pipeline to support multiple TTS engine selection
4. Add pytest tests for VOICEVOX integration
5. Document setup and usage

**Estimated Effort**: 2-3 days

### 4.3 Long-term (3-6 months)

**TTS Engine Abstraction**
- Create unified TTS interface (`src/core/tts/engine_base.py`)
- Implement adapters for SofTalk, VOICEVOX, Cloud APIs
- Add engine selection to project configuration
- Enable runtime switching between engines

**Benefits:**
- Future-proof architecture
- Easy to add new engines
- Consistent API across engines
- Better testing and maintenance

**Estimated Effort**: 5-7 days

---

## 5. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| SofTalk installation issues | High | Medium | Provide detailed setup guide, Docker alternative |
| Voice quality complaints | Medium | Medium | Offer VOICEVOX as alternative |
| Licensing issues (AquesTalk) | Low | High | Document licensing requirements, prefer SofTalk/VOICEVOX |
| Performance bottleneck (large timelines) | Medium | Low | Implement parallel processing |
| API breaking changes (VOICEVOX) | Low | Medium | Version pinning, integration tests |

---

## 6. Conclusion

**Current Status**: ✅ **SofTalk integration is functional and production-ready**

**Recommendation**:
- **Short-term**: Continue using SofTalk, improve documentation
- **Mid-term**: Add VOICEVOX support for better quality
- **Long-term**: Implement TTS abstraction layer for flexibility

**Technical Feasibility**: ✅ **High** - All recommended improvements are technically achievable with reasonable effort.

**Decision**: TASK_014 SofTalk integration can be marked as **EVALUATED** with recommendation to proceed with documentation improvements and VOICEVOX exploration in future iterations.

---

## References

- [TASK_008 SofTalk Integration](../tasks/TASK_008_SofTalkIntegration.md)
- [TASK_014 Audio Output Optimization](../tasks/TASK_014_AudioOutputOptimization.md)
- [SofTalk Official Site](https://w.atwiki.jp/softalk/)
- [VOICEVOX Official Site](https://voicevox.hiroshiba.jp/)
- [AquesTalk Documentation](https://www.a-quest.com/products/aquestalk.html)

---

**Next Steps:**
1. Review this assessment with stakeholders
2. Prioritize VOICEVOX integration based on user feedback
3. Update project roadmap with TTS improvements

**Status**: ✅ TASK_014 SofTalk Integration Assessment Complete
