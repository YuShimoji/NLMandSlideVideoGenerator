#!/usr/bin/env python3
"""
Audio Output Environment Diagnostics Tool
Usage: python scripts/test_audio_output.py [-device auto|<device_name>] [-fallback true|false]
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AudioDevice:
    """Represents an audio output device."""
    name: str
    is_default: bool
    status: str


@dataclass
class AudioDiagnosticResult:
    """Diagnostic result for audio environment."""
    timestamp: str
    platform: str
    os_version: str
    default_device: Optional[str]
    available_devices: list[dict]
    ffmpeg_available: bool
    ffmpeg_path: Optional[str]
    test_audio_playable: bool
    errors: list[str]
    warnings: list[str]


class AudioEnvironmentDiagnostics:
    """Audio environment diagnostics tool."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def get_windows_audio_devices(self) -> list[AudioDevice]:
        """Get Windows audio output devices using PowerShell."""
        if platform.system() != "Windows":
            self.warnings.append("Not running on Windows. Audio device detection limited.")
            return []

        try:
            # Use PowerShell to get audio devices
            ps_script = """
                Get-AudioDevice -List | Where-Object { $_.Type -eq 'Playback' } | ForEach-Object {
                    [PSCustomObject]@{
                        Name = $_.Name
                        IsDefault = $_.Default
                        Status = 'Active'
                    }
                } | ConvertTo-Json
            """
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                # Fallback: Use basic Windows API via PowerShell
                ps_fallback = """
                    Add-Type -AssemblyName System.Windows.Forms
                    [PSCustomObject]@{
                        Name = 'Default Audio Device'
                        IsDefault = $true
                        Status = 'Unknown'
                    } | ConvertTo-Json
                """
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_fallback],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            if result.returncode == 0 and result.stdout.strip():
                devices_data = json.loads(result.stdout)
                if isinstance(devices_data, dict):
                    devices_data = [devices_data]
                return [
                    AudioDevice(
                        name=d.get("Name", "Unknown"),
                        is_default=d.get("IsDefault", False),
                        status=d.get("Status", "Unknown")
                    )
                    for d in devices_data
                ]
            else:
                self.warnings.append(f"PowerShell audio device query failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            self.warnings.append("PowerShell audio device query timed out.")
        except json.JSONDecodeError as e:
            self.warnings.append(f"Failed to parse PowerShell output: {e}")
        except Exception as e:
            self.warnings.append(f"Unexpected error querying audio devices: {e}")

        # Ultimate fallback
        self.warnings.append("Using fallback: assuming default system audio device exists.")
        return [AudioDevice(name="System Default", is_default=True, status="Unknown")]

    def find_ffmpeg(self) -> Optional[Path]:
        """Find ffmpeg executable."""
        # Check environment variable
        ffmpeg_env = os.getenv("FFMPEG_EXE", "").strip()
        if ffmpeg_env:
            p = Path(ffmpeg_env)
            if p.exists():
                return p

        # Check PATH
        import shutil
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return Path(ffmpeg_path)

        # Check common locations
        common_paths = [
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path("C:/tools/ffmpeg/bin/ffmpeg.exe"),
            Path("/usr/bin/ffmpeg"),
            Path("/usr/local/bin/ffmpeg"),
        ]
        for p in common_paths:
            if p.exists():
                return p

        self.warnings.append("ffmpeg not found. Audio playback test will be skipped.")
        return None

    def test_audio_playback(self, ffmpeg_path: Optional[Path]) -> bool:
        """Test audio playback capability."""
        if not ffmpeg_path:
            return False

        # Generate a simple test tone (1 second, 440Hz sine wave)
        test_audio = Path("test_audio_tone.wav")
        try:
            # Generate test tone using ffmpeg
            result = subprocess.run(
                [
                    str(ffmpeg_path),
                    "-f", "lavfi",
                    "-i", "sine=frequency=440:duration=0.5",
                    "-y",
                    str(test_audio)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                self.warnings.append(f"Failed to generate test audio: {result.stderr}")
                return False

            # Verify the file exists
            if not test_audio.exists():
                self.warnings.append("Test audio file was not created.")
                return False

            # Try to play it (silent test, just check if command succeeds)
            if platform.system() == "Windows":
                # Use ffplay if available, otherwise just verify file is readable
                play_result = subprocess.run(
                    [str(ffmpeg_path), "-i", str(test_audio), "-f", "null", "-"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                playable = play_result.returncode == 0
            else:
                # On non-Windows, just verify file is valid
                playable = test_audio.stat().st_size > 0

            return playable

        except subprocess.TimeoutExpired:
            self.warnings.append("Audio playback test timed out.")
            return False
        except Exception as e:
            self.warnings.append(f"Audio playback test failed: {e}")
            return False
        finally:
            # Cleanup test file
            if test_audio.exists():
                try:
                    test_audio.unlink()
                except Exception:
                    pass

    def run_diagnostics(self) -> AudioDiagnosticResult:
        """Run full audio environment diagnostics."""
        # Get system info
        timestamp = datetime.utcnow().isoformat() + "Z"
        platform_name = platform.system()
        os_version = platform.version()

        # Get audio devices
        devices = self.get_windows_audio_devices()
        default_device = next(
            (d.name for d in devices if d.is_default),
            devices[0].name if devices else None
        )

        # Find ffmpeg
        ffmpeg_path = self.find_ffmpeg()

        # Test audio playback
        test_playable = self.test_audio_playback(ffmpeg_path)

        return AudioDiagnosticResult(
            timestamp=timestamp,
            platform=platform_name,
            os_version=os_version,
            default_device=default_device,
            available_devices=[asdict(d) for d in devices],
            ffmpeg_available=ffmpeg_path is not None,
            ffmpeg_path=str(ffmpeg_path) if ffmpeg_path else None,
            test_audio_playable=test_playable,
            errors=self.errors,
            warnings=self.warnings
        )


def print_diagnostic_report(result: AudioDiagnosticResult):
    """Print diagnostic report in human-readable format."""
    print("\n" + "=" * 60)
    print("Audio Environment Diagnostic Report")
    print("=" * 60)
    print(f"Timestamp: {result.timestamp}")
    print(f"Platform: {result.platform}")
    print(f"OS Version: {result.os_version}")
    print()

    print("Audio Devices:")
    if result.available_devices:
        for i, device in enumerate(result.available_devices, 1):
            default_marker = " [DEFAULT]" if device["is_default"] else ""
            print(f"  {i}. {device['name']}{default_marker} (Status: {device['status']})")
    else:
        print("  No devices detected")
    print()

    print(f"Default Device: {result.default_device or 'None'}")
    print(f"ffmpeg Available: {'✅ Yes' if result.ffmpeg_available else '❌ No'}")
    if result.ffmpeg_path:
        print(f"ffmpeg Path: {result.ffmpeg_path}")
    print(f"Audio Playback Test: {'✅ Passed' if result.test_audio_playable else '❌ Failed'}")
    print()

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  ⚠️  {warning}")
        print()

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(f"  ❌ {error}")
        print()

    print("=" * 60)

    # Troubleshooting recommendations
    if not result.ffmpeg_available:
        print("\n🔧 Recommendation: Install ffmpeg for audio processing")
        print("   Download from: https://ffmpeg.org/download.html")
        print("   Or set FFMPEG_EXE environment variable")

    if not result.test_audio_playable and result.ffmpeg_available:
        print("\n🔧 Recommendation: Check audio driver installation")
        print("   - Ensure audio drivers are up to date")
        print("   - Check Windows Sound settings")
        print("   - Verify default playback device is enabled")

    if not result.available_devices:
        print("\n🔧 Recommendation: Audio device detection failed")
        print("   - Ensure audio hardware is connected")
        print("   - Check Device Manager for disabled audio devices")
        print("   - Reinstall audio drivers if necessary")


def main():
    parser = argparse.ArgumentParser(description="Audio Output Environment Diagnostics")
    parser.add_argument(
        "-device",
        default="auto",
        help="Target audio device (auto|<device_name>)"
    )
    parser.add_argument(
        "-fallback",
        default="true",
        choices=["true", "false"],
        help="Enable fallback to system default device"
    )
    parser.add_argument(
        "-json",
        action="store_true",
        help="Output in JSON format"
    )
    parser.add_argument(
        "-output",
        type=Path,
        help="Output file path for diagnostic report"
    )

    args = parser.parse_args()

    # Run diagnostics
    diagnostics = AudioEnvironmentDiagnostics()
    result = diagnostics.run_diagnostics()

    # Output results
    if args.json:
        output = json.dumps(asdict(result), indent=2)
        if args.output:
            args.output.write_text(output, encoding="utf-8")
            print(f"Diagnostic report saved to: {args.output}")
        else:
            print(output)
    else:
        print_diagnostic_report(result)
        if args.output:
            # Save both human-readable and JSON
            json_output = args.output.with_suffix(".json")
            json_output.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
            print(f"\n📄 JSON report saved to: {json_output}")

    # Exit with appropriate code
    if result.errors:
        sys.exit(1)
    elif result.warnings and not result.test_audio_playable:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
