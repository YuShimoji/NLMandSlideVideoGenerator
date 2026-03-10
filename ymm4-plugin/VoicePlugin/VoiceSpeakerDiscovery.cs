using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using YukkuriMovieMaker.Plugin.Voice;

namespace NLMSlidePlugin.VoicePlugin
{
    /// <summary>
    /// YMM4 ランタイムから利用可能な IVoiceSpeaker を収集する。
    ///
    /// 3層フォールバック:
    ///   1. AppDomain.GetAssemblies() から IVoicePlugin を探索
    ///   2. MainWindow.DataContext からリフレクションで探索
    ///   3. 空リスト + エラーログ
    /// </summary>
    public static class VoiceSpeakerDiscovery
    {
        /// <summary>
        /// 利用可能な全 IVoiceSpeaker を収集する。
        /// </summary>
        /// <param name="errors">探索中に発生したエラーメッセージ</param>
        /// <returns>発見した IVoiceSpeaker の一覧</returns>
        public static IReadOnlyList<IVoiceSpeaker> GetAvailableSpeakers(out List<string> errors)
        {
            errors = new List<string>();
            var speakers = new List<IVoiceSpeaker>();

            // Layer 1: AppDomain アセンブリスキャン
            try
            {
                var found = ScanAppDomainAssemblies();
                if (found.Count > 0)
                {
                    speakers.AddRange(found);
                    return speakers;
                }
            }
            catch (Exception ex)
            {
                errors.Add($"AppDomain scan failed: {ex.Message}");
            }

            // Layer 2: MainWindow DataContext リフレクション
            try
            {
                var found = ScanMainWindowDataContext();
                if (found.Count > 0)
                {
                    speakers.AddRange(found);
                    return speakers;
                }
            }
            catch (Exception ex)
            {
                errors.Add($"MainWindow scan failed: {ex.Message}");
            }

            // Layer 3: 空リスト
            if (speakers.Count == 0)
            {
                errors.Add("No IVoiceSpeaker found in runtime. Voice generation will be skipped.");
            }

            return speakers;
        }

        /// <summary>
        /// AppDomain 内の全アセンブリから IVoicePlugin 実装を探索し、
        /// それぞれの Voices プロパティから IVoiceSpeaker を収集する。
        /// </summary>
        private static List<IVoiceSpeaker> ScanAppDomainAssemblies()
        {
            var speakers = new List<IVoiceSpeaker>();

            foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies())
            {
                Type[] types;
                try
                {
                    types = assembly.GetTypes();
                }
                catch (ReflectionTypeLoadException ex)
                {
                    // 一部の型がロードできない場合、ロードできた型だけ処理
                    types = ex.Types.Where(t => t != null).ToArray()!;
                }
                catch
                {
                    continue;
                }

                foreach (var type in types)
                {
                    if (type.IsAbstract || type.IsInterface)
                        continue;

                    if (!typeof(IVoicePlugin).IsAssignableFrom(type))
                        continue;

                    try
                    {
                        // IVoicePlugin のインスタンスを取得
                        // YMM4 はプラグインをシングルトンで管理しているため、
                        // 既存インスタンスを探すほうが安全
                        var voicesProperty = type.GetProperty("Voices",
                            BindingFlags.Public | BindingFlags.Instance);
                        if (voicesProperty == null)
                            continue;

                        // 静的インスタンスフィールドを探す
                        var instance = FindSingletonInstance(type);
                        if (instance == null)
                            continue;

                        var voices = voicesProperty.GetValue(instance) as IEnumerable<IVoiceSpeaker>;
                        if (voices != null)
                        {
                            speakers.AddRange(voices);
                        }
                    }
                    catch
                    {
                        // 個別の型でエラーが起きても他の型の探索を続行
                    }
                }
            }

            return speakers;
        }

        /// <summary>
        /// MainWindow.DataContext からリフレクションで IVoiceSpeaker 一覧を探索する。
        /// YMM4 の内部構造に依存するフォールバック手段。
        /// </summary>
        private static List<IVoiceSpeaker> ScanMainWindowDataContext()
        {
            var speakers = new List<IVoiceSpeaker>();

            var mainWindow = System.Windows.Application.Current?.MainWindow;
            if (mainWindow == null)
                return speakers;

            var dataContext = mainWindow.DataContext;
            if (dataContext == null)
                return speakers;

            // DataContext のプロパティを再帰的に探索して IVoiceSpeaker を見つける
            var visited = new HashSet<object>(ReferenceEqualityComparer.Instance);
            SearchForVoiceSpeakers(dataContext, speakers, visited, maxDepth: 5);

            return speakers;
        }

        /// <summary>
        /// オブジェクトグラフを再帰的に探索して IVoiceSpeaker/IVoicePlugin を見つける。
        /// </summary>
        private static void SearchForVoiceSpeakers(
            object obj,
            List<IVoiceSpeaker> speakers,
            HashSet<object> visited,
            int maxDepth)
        {
            if (maxDepth <= 0 || obj == null || !visited.Add(obj))
                return;

            var type = obj.GetType();

            // IVoicePlugin を見つけた場合、その Voices を取得
            if (obj is IVoicePlugin voicePlugin)
            {
                try
                {
                    var voices = voicePlugin.Voices;
                    if (voices != null)
                        speakers.AddRange(voices);
                }
                catch
                {
                    // Voices 取得に失敗しても続行
                }
                return;
            }

            // IEnumerable<IVoiceSpeaker> を見つけた場合
            if (obj is IEnumerable<IVoiceSpeaker> speakerCollection)
            {
                try
                {
                    speakers.AddRange(speakerCollection);
                }
                catch
                {
                    // 列挙に失敗しても続行
                }
                return;
            }

            // プロパティを再帰探索
            foreach (var prop in type.GetProperties(BindingFlags.Public | BindingFlags.Instance))
            {
                if (!prop.CanRead || prop.GetIndexParameters().Length > 0)
                    continue;

                // 基本型はスキップ
                if (prop.PropertyType.IsPrimitive || prop.PropertyType == typeof(string))
                    continue;

                try
                {
                    var value = prop.GetValue(obj);
                    if (value != null)
                    {
                        SearchForVoiceSpeakers(value, speakers, visited, maxDepth - 1);
                    }
                }
                catch
                {
                    // リフレクション例外は無視して続行
                }
            }
        }

        /// <summary>
        /// 型のシングルトンインスタンスを探す。
        /// </summary>
        private static object? FindSingletonInstance(Type type)
        {
            // パターン1: static Instance プロパティ
            var instanceProp = type.GetProperty("Instance",
                BindingFlags.Public | BindingFlags.Static);
            if (instanceProp != null)
            {
                try
                {
                    return instanceProp.GetValue(null);
                }
                catch { }
            }

            // パターン2: static フィールド
            foreach (var field in type.GetFields(BindingFlags.Static | BindingFlags.NonPublic | BindingFlags.Public))
            {
                if (type.IsAssignableFrom(field.FieldType))
                {
                    try
                    {
                        return field.GetValue(null);
                    }
                    catch { }
                }
            }

            return null;
        }
    }
}
