using System;
using System.IO;

namespace NLMSlidePlugin.Core
{
    /// <summary>
    /// WAVファイルヘッダーを直接解析して再生時間を取得する。
    /// NAudioへの依存なし。
    /// </summary>
    public static class WavDurationReader
    {
        private const double DefaultDurationSeconds = 3.0;

        /// <summary>
        /// WAVファイルの再生時間（秒）を取得する。
        /// 解析失敗時はデフォルト値（3.0秒）を返す。
        /// </summary>
        public static double GetDuration(string filePath)
        {
            try
            {
                using var stream = File.OpenRead(filePath);
                return ParseWavDuration(stream);
            }
            catch (FileNotFoundException)
            {
                return DefaultDurationSeconds;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[WavDurationReader] Failed to parse: {filePath} - {ex.Message}");
                return DefaultDurationSeconds;
            }
        }

        private static double ParseWavDuration(Stream stream)
        {
            using var reader = new BinaryReader(stream);

            // RIFF header
            var riffId = new string(reader.ReadChars(4));
            if (riffId != "RIFF")
                return DefaultDurationSeconds;

            reader.ReadInt32(); // file size

            var waveId = new string(reader.ReadChars(4));
            if (waveId != "WAVE")
                return DefaultDurationSeconds;

            int sampleRate = 0;
            int bitsPerSample = 0;
            int channels = 0;
            int dataSize = -1;

            // チャンクを探索
            while (stream.Position < stream.Length - 8)
            {
                var chunkId = new string(reader.ReadChars(4));
                int chunkSize = reader.ReadInt32();

                if (chunkId == "fmt ")
                {
                    var audioFormat = reader.ReadInt16();
                    channels = reader.ReadInt16();
                    sampleRate = reader.ReadInt32();
                    reader.ReadInt32(); // byte rate
                    reader.ReadInt16(); // block align
                    bitsPerSample = reader.ReadInt16();

                    // fmt チャンクの残りをスキップ
                    int remaining = chunkSize - 16;
                    if (remaining > 0)
                        reader.ReadBytes(remaining);
                }
                else if (chunkId == "data")
                {
                    dataSize = chunkSize;
                    break; // data チャンクが見つかれば終了
                }
                else
                {
                    // 不明チャンクをスキップ
                    if (chunkSize > 0 && stream.Position + chunkSize <= stream.Length)
                        reader.ReadBytes(chunkSize);
                    else
                        break;
                }
            }

            if (sampleRate <= 0 || bitsPerSample <= 0 || channels <= 0 || dataSize <= 0)
                return DefaultDurationSeconds;

            int bytesPerSample = bitsPerSample / 8;
            int totalSamples = dataSize / (bytesPerSample * channels);
            return (double)totalSamples / sampleRate;
        }
    }
}
