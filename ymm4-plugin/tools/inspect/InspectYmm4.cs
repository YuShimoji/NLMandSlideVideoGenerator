using System;
using System.Linq;
using System.Reflection;

// Inspect Animation type (Opacity/Zoom property type on VisualItem)
var dllPath = @"D:\YukkuriMovieMaker_v4\YukkuriMovieMaker.dll";
var asm = Assembly.LoadFrom(dllPath);
Type[] types;
try { types = asm.GetTypes(); }
catch (ReflectionTypeLoadException ex) { types = ex.Types.Where(t => t != null).ToArray()!; }

var imageItemType = types.First(t => t?.Name == "ImageItem");
var opacityProp = imageItemType.GetProperty("Opacity");
Console.WriteLine($"Opacity property type: {opacityProp!.PropertyType.FullName}");

var animType = opacityProp.PropertyType;
Console.WriteLine($"\nAnimation type: {animType.FullName}");
Console.WriteLine($"  Base: {animType.BaseType?.FullName}");

Console.WriteLine("\n=== Animation PROPERTIES ===");
foreach (var p in animType.GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(p => p.Name))
{
    Console.WriteLine($"  {p.PropertyType.Name} {p.Name} {{ {(p.CanRead ? "get " : "")}{(p.CanWrite ? "set " : "")}}}");
}

Console.WriteLine("\n=== Animation METHODS ===");
foreach (var m in animType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
{
    if (m.IsSpecialName) continue;
    var parms = string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
    Console.WriteLine($"  {m.ReturnType.Name} {m.Name}({parms})");
}

// Check Values property type
var valuesProp = animType.GetProperty("Values");
if (valuesProp != null)
{
    Console.WriteLine($"\n=== Values property ===");
    Console.WriteLine($"  Type: {valuesProp.PropertyType.FullName}");
    Console.WriteLine($"  CanRead: {valuesProp.CanRead}, CanWrite: {valuesProp.CanWrite}");

    // Check the element type
    var valuesType = valuesProp.PropertyType;
    if (valuesType.IsGenericType)
    {
        var elementType = valuesType.GetGenericArguments()[0];
        Console.WriteLine($"  Element type: {elementType.FullName}");
        Console.WriteLine("\n=== AnimationValue PROPERTIES ===");
        foreach (var p in elementType.GetProperties(BindingFlags.Public | BindingFlags.Instance).OrderBy(p => p.Name))
            Console.WriteLine($"    {p.PropertyType.Name} {p.Name} {{ {(p.CanRead ? "get " : "")}{(p.CanWrite ? "set " : "")}}}");
    }
}

// Try to create an ImageItem and check default opacity
Console.WriteLine("\n=== Default ImageItem Opacity ===");
try
{
    var img = Activator.CreateInstance(imageItemType);
    var opacity = opacityProp.GetValue(img);
    var vals = valuesProp!.GetValue(opacity);
    var countProp = vals!.GetType().GetProperty("Count");
    int count = (int)countProp!.GetValue(vals)!;
    Console.WriteLine($"  Count: {count}");
    var indexer = vals.GetType().GetProperty("Item");
    if (indexer != null && count > 0)
    {
        var first = indexer.GetValue(vals, new object[] { 0 });
        var vp = first!.GetType().GetProperty("Value");
        Console.WriteLine($"  Values[0].Value: {vp!.GetValue(first)}");
    }
}
catch (Exception ex)
{
    Console.WriteLine($"  Error: {ex.Message}");
}
