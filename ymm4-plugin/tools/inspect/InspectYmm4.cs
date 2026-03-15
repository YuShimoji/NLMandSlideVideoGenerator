using System;
using System.Linq;
using System.Reflection;

var dllPath = @"D:\YukkuriMovieMaker_v4\YukkuriMovieMaker.dll";
var asm = Assembly.LoadFrom(dllPath);
Type[] types;
try { types = asm.GetTypes(); }
catch (ReflectionTypeLoadException ex) { types = ex.Types.Where(t => t != null).ToArray()!; }

// Find ImageItem
var imageItemType = types.FirstOrDefault(t => t?.Name == "ImageItem");
if (imageItemType == null)
{
    Console.WriteLine("ImageItem not found!");
    // Search for anything with "Image" in the name
    foreach (var t in types.Where(t => t?.Name?.Contains("Image") == true).Take(20))
        Console.WriteLine($"  Found: {t!.FullName}");
    return;
}

Console.WriteLine($"TYPE: {imageItemType.FullName}");
Console.WriteLine($"  BASE: {imageItemType.BaseType?.FullName}");
foreach (var iface in imageItemType.GetInterfaces().Take(10))
    Console.WriteLine($"  IFACE: {iface.FullName}");

// Constructors
Console.WriteLine("\n=== CONSTRUCTORS ===");
foreach (var ctor in imageItemType.GetConstructors(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance))
{
    var parms = string.Join(", ", ctor.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
    Console.WriteLine($"  CTOR({parms})");
}

// Properties (including inherited)
Console.WriteLine("\n=== PROPERTIES (declared + inherited) ===");
var allProps = imageItemType.GetProperties(BindingFlags.Public | BindingFlags.Instance);
foreach (var p in allProps.OrderBy(p => p.Name))
{
    var declType = p.DeclaringType?.Name ?? "?";
    var get = p.CanRead ? "get" : "";
    var set = p.CanWrite ? "set" : "";
    Console.WriteLine($"  [{declType}] {p.PropertyType.Name} {p.Name} {{ {get} {set} }}");
}

// FilePath specifically
Console.WriteLine("\n=== FilePath details ===");
var fpProp = imageItemType.GetProperty("FilePath");
if (fpProp != null)
{
    Console.WriteLine($"  Type: {fpProp.PropertyType.FullName}");
    Console.WriteLine($"  DeclaringType: {fpProp.DeclaringType?.FullName}");
    Console.WriteLine($"  CanRead: {fpProp.CanRead}, CanWrite: {fpProp.CanWrite}");
}

// ContentFilePath, SourceFilePath, etc.
foreach (var name in new[] { "ContentFilePath", "SourceFilePath", "ImagePath", "Path", "Source", "Bitmap", "ImageSource" })
{
    var prop = allProps.FirstOrDefault(p => p.Name == name);
    if (prop != null)
        Console.WriteLine($"  Found: {prop.PropertyType.Name} {name}");
}

// Methods (declared only)
Console.WriteLine("\n=== METHODS (declared) ===");
foreach (var m in imageItemType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
{
    if (m.IsSpecialName) continue; // skip get_/set_
    var parms = string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
    Console.WriteLine($"  {m.ReturnType.Name} {m.Name}({parms})");
}

// Also check base class methods
Console.WriteLine("\n=== BASE CLASS METHODS ===");
var baseType = imageItemType.BaseType;
if (baseType != null)
{
    Console.WriteLine($"Base: {baseType.FullName}");
    foreach (var m in baseType.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
    {
        if (m.IsSpecialName) continue;
        var parms = string.Join(", ", m.GetParameters().Select(p => $"{p.ParameterType.Name} {p.Name}"));
        Console.WriteLine($"  {m.ReturnType.Name} {m.Name}({parms})");
    }
}
