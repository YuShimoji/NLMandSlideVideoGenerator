using System;
using System.IO;
using System.Collections.Generic;
using Xunit;
using NLMSlidePlugin.Core;

namespace NLMSlidePlugin.Tests
{
    public class WavDurationReaderTests : IDisposable
    {
        private readonly List<string> _tempFiles = new();

        public void Dispose()
        {
            foreach (var f in _tempFiles)
            {
                try { File.Delete(f); } catch (IOException) { }
            }
        }

        private string CreateTempWav(int sampleRate, int channels, int bitsPerSample, int durationMs)
        {
            var path = Path.GetTempFileName();
            _tempFiles.Add(path);

            int bytesPerSample = bitsPerSample / 8;
            int totalSamples = sampleRate * durationMs / 1000;
            int dataSize = totalSamples * channels * bytesPerSample;

            using var stream = File.Create(path);
            using var writer = new BinaryWriter(stream);

            // RIFF header
            writer.Write("RIFF".ToCharArray());
            writer.Write(36 + dataSize); // file size - 8
            writer.Write("WAVE".ToCharArray());

            // fmt chunk
            writer.Write("fmt ".ToCharArray());
            writer.Write(16); // chunk size
            writer.Write((short)1); // PCM format
            writer.Write((short)channels);
            writer.Write(sampleRate);
            writer.Write(sampleRate * channels * bytesPerSample); // byte rate
            writer.Write((short)(channels * bytesPerSample)); // block align
            writer.Write((short)bitsPerSample);

            // data chunk
            writer.Write("data".ToCharArray());
            writer.Write(dataSize);
            writer.Write(new byte[dataSize]); // silence

            return path;
        }

        [Fact]
        public void GetDuration_ValidMonoWav_ReturnsCorrectDuration()
        {
            var path = CreateTempWav(44100, 1, 16, 2000); // 2 seconds
            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(2.0, duration, precision: 1);
        }

        [Fact]
        public void GetDuration_ValidStereoWav_ReturnsCorrectDuration()
        {
            var path = CreateTempWav(44100, 2, 16, 3000); // 3 seconds
            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(3.0, duration, precision: 1);
        }

        [Fact]
        public void GetDuration_HighSampleRate_ReturnsCorrectDuration()
        {
            var path = CreateTempWav(48000, 2, 16, 5000); // 5 seconds
            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(5.0, duration, precision: 1);
        }

        [Fact]
        public void GetDuration_ShortDuration_ReturnsCorrectDuration()
        {
            var path = CreateTempWav(44100, 1, 16, 500); // 0.5 seconds
            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(0.5, duration, precision: 1);
        }

        [Fact]
        public void GetDuration_NonExistentFile_ReturnsDefault()
        {
            var duration = WavDurationReader.GetDuration("/nonexistent/file.wav");
            Assert.Equal(3.0, duration);
        }

        [Fact]
        public void GetDuration_InvalidFile_ReturnsDefault()
        {
            var path = Path.GetTempFileName();
            _tempFiles.Add(path);
            File.WriteAllText(path, "This is not a WAV file");

            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(3.0, duration);
        }

        [Fact]
        public void GetDuration_EmptyFile_ReturnsDefault()
        {
            var path = Path.GetTempFileName();
            _tempFiles.Add(path);
            // File is already empty from GetTempFileName

            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(3.0, duration);
        }

        [Fact]
        public void GetDuration_TruncatedHeader_ReturnsDefault()
        {
            var path = Path.GetTempFileName();
            _tempFiles.Add(path);
            File.WriteAllBytes(path, new byte[] { 0x52, 0x49, 0x46, 0x46 }); // "RIFF" only

            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(3.0, duration);
        }

        [Fact]
        public void GetDuration_WavWithExtraChunks_ReturnsCorrectDuration()
        {
            // WAV with an extra "LIST" chunk before data
            var path = Path.GetTempFileName();
            _tempFiles.Add(path);

            int sampleRate = 44100;
            int channels = 1;
            int bitsPerSample = 16;
            int bytesPerSample = bitsPerSample / 8;
            int durationMs = 1000;
            int totalSamples = sampleRate * durationMs / 1000;
            int dataSize = totalSamples * channels * bytesPerSample;
            int listChunkSize = 16;

            using (var stream = File.Create(path))
            using (var writer = new BinaryWriter(stream))
            {
                // RIFF header
                writer.Write("RIFF".ToCharArray());
                writer.Write(36 + dataSize + 8 + listChunkSize);
                writer.Write("WAVE".ToCharArray());

                // fmt chunk
                writer.Write("fmt ".ToCharArray());
                writer.Write(16);
                writer.Write((short)1);
                writer.Write((short)channels);
                writer.Write(sampleRate);
                writer.Write(sampleRate * channels * bytesPerSample);
                writer.Write((short)(channels * bytesPerSample));
                writer.Write((short)bitsPerSample);

                // Extra LIST chunk (should be skipped)
                writer.Write("LIST".ToCharArray());
                writer.Write(listChunkSize);
                writer.Write(new byte[listChunkSize]);

                // data chunk
                writer.Write("data".ToCharArray());
                writer.Write(dataSize);
                writer.Write(new byte[dataSize]);
            }

            var duration = WavDurationReader.GetDuration(path);
            Assert.Equal(1.0, duration, precision: 1);
        }
    }
}
