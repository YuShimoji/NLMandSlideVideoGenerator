using System;
using System.Linq;
using System.Reflection;

// Phase 3: Timeline, Scene, VoiceItem creation pipeline, IVoiceSpeaker

var dllPaths = new[] {
    @"D:\YukkuriMovieMaker_v4\YukkuriMovieMaker.dll",
    @"D:\YukkuriMovieMaker_v4\YukkuriMovieMaker.Plugin.dll",
};

// Target specific types for deep inspection (exact type names after last '.')
var targetTypes = new[] {
    "YukkuriMovieMaker.Project.Timeline",
    "YukkuriMovieMaker.Project.Scene",
    "YukkuriMovieMaker.Project.YmmProject",
    "YukkuriMovieMaker.ViewModels.TimelineViewModel",
    "YukkuriMovieMaker.Plugin.VoiceFactory",
    "YukkuriMovieMaker.Plugin.Voice.IVoiceSpeaker",
    "YukkuriMovieMaker.Plugin.Voice.VoiceDescription",
    "YukkuriMovieMaker.Plugin.Voice.IVoiceParameter",
    "YukkuriMovieMaker.Plugin.Voice.IVoicePronounce",
    "YukkuriMovieMaker.Plugin.Voice.IVoicePlugin",
    "YukkuriMovieMaker.ViewModels.CommandParameter.AddVoiceItemCommandParameter",
    "YukkuriMovieMaker.Project.Items.IItem",
    "YukkuriMovieMaker.Project.Items.BaseItem",
    "YukkuriMovieMaker.Project.Items.ICharacterItem",
    "YukkuriMovieMaker.Views.Commands.YMMCommands",
};

foreach (var dllPath in dllPaths)
{
    Console.WriteLine($"\n===== {System.IO.Path.GetFileName(dllPath)} =====");
    try
    {
        var asm = Assembly.LoadFrom(dllPath);
        Type[] types;
        try { types = asm.GetTypes(); }
        catch (ReflectionTypeLoadException ex) { types = ex.Types.Where(t => t != null).ToArray()!; }

        foreach (var t in types)
        {
            if (t == null) continue;
            var name = t.FullName ?? t.Name;

            bool isTarget = targetTypes.Any(k => name == k);
            if (!isTarget) continue;

            Console.WriteLine($"\nTYPE: {name}");
            if (t.BaseType != null && t.BaseType != typeof(object))
                Console.WriteLine($"  BASE: {t.BaseType.FullName}");

            var interfaces = t.GetInterfaces();
            foreach (var iface in interfaces.Take(5))
                Console.WriteLine($"  IFACE: {iface.FullName}");

            try
            {
                var methods = t.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                foreach (var m in methods)
                {
                    // Skip compiler-generated lambda methods
                    if (m.Name.Contains("__")) continue;

                    try
                    {
                        var parms = string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
                        Console.WriteLine($"  METHOD: {m.ReturnType.Name} {m.Name}({parms})");
                    }
                    catch (Exception ex) { Console.WriteLine($"  METHOD_ERR: {m.Name} - {ex.Message}"); }
                }
            }
            catch { }

            try
            {
                var props = t.GetProperties(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.DeclaredOnly);
                foreach (var p in props)
                    Console.WriteLine($"  PROP: {p.PropertyType.Name} {p.Name}");
            }
            catch { }

            try
            {
                var fields = t.GetFields(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly);
                foreach (var f in fields)
                {
                    if (f.Name.Contains("__")) continue;
                    Console.WriteLine($"  FIELD: {f.FieldType.Name} {f.Name}");
                }
            }
            catch { }
        }
    }
    catch (Exception ex)
    {
        Console.WriteLine($"LOAD ERROR: {ex.Message}");
    }
}
