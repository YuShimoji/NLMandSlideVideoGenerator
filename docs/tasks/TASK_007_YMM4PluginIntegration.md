# Task: YMM4繝励Λ繧ｰ繧､繝ｳ騾｣謳ｺ螳溯｣・
Status: DONE
Tier: 2
Branch: feature/ymm4-plugin
Owner: Worker
Created: 2026-02-02T03:59:00Z
Report: docs/inbox/REPORT_TASK_007_ScenarioB_2026-02-23.md

## 螳御ｺ・＠縺滉ｽ懈･ｭ

### 繧ｷ繝翫Μ繧ｪZero・・4・牙ｮ御ｺ・
- [x] Directory.Build.props 閾ｪ蜍募喧繧ｹ繧ｯ繝ｪ繝励ヨ菴懈・
- [x] 繝薙Ν繝峨・繝ｭ繧ｻ繧ｹ閾ｪ蜍募喧・・uild_plugin.bat・・
- [x] 繧ｻ繝・ヨ繧｢繝・・繧ｬ繧､繝我ｽ懈・・・ETUP_GUIDE.md・・
- [x] README譖ｴ譁ｰ・医け繧､繝・け繧ｹ繧ｿ繝ｼ繝郁ｿｽ蜉・・
- [x] .NET 9.0蟇ｾ蠢懃｢ｺ隱・
- [x] Git蜿肴丐螳御ｺ・ｼ医さ繝溘ャ繝・ 556591d・・

### 繧ｷ繝翫Μ繧ｪA螳溯｣・ｮ御ｺ・
- [x] CsvTimelineReader.cs - UTF-8蟇ｾ蠢廚SV繝代・繧ｵ繝ｼ縲√ム繝悶Ν繧ｯ繧ｩ繝ｼ繝亥ｯｾ蠢・
- [x] CsvTimelineItem.cs - 繧ｿ繧､繝繝ｩ繧､繝ｳ陦後ョ繝ｼ繧ｿ繝｢繝・Ν
- [x] CsvImportDialog.xaml/.cs - WPF繧､繝ｳ繝昴・繝医ム繧､繧｢繝ｭ繧ｰ
- [x] Ymm4TimelineImporter.cs - YMM4騾｣謳ｺ繝ｭ繧ｸ繝・け
- [x] CsvTimelineVoicePlugin.cs - 繝懊う繧ｹ繝励Λ繧ｰ繧､繝ｳ譖ｴ譁ｰ
- [x] CSV隱ｭ縺ｿ霎ｼ縺ｿ・郁ｩｱ閠・繝・く繧ｹ繝亥ｽ｢蠑擾ｼ・
- [x] WAV繝輔ぃ繧､繝ｫ邏蝉ｻ倥￠・・01.wav・櫁｡檎分蜿ｷ蟇ｾ蠢懶ｼ・
- [x] 繧ｿ繧､繝繝ｩ繧､繝ｳ譎ょ綾閾ｪ蜍戊ｨ育ｮ・
- [x] 隧ｱ閠・・繝懊う繧ｹ繝槭ャ繝斐Φ繧ｰ
- [x] 繝励Ξ繝薙Η繝ｼ陦ｨ遉ｺ
- [x] Git蜿肴丐螳御ｺ・ｼ医さ繝溘ャ繝・ a797c80・・

## Objective
- YMM4・医ｆ縺｣縺上ｊ繝繝ｼ繝薙・繝｡繝ｼ繧ｫ繝ｼ4・峨・繝ｩ繧ｰ繧､繝ｳ繧貞ｮ溯｣・＠縲，SV 繧ｿ繧､繝繝ｩ繧､繝ｳ縺九ｉ閾ｪ蜍慕噪縺ｫ髻ｳ螢ｰ繝ｻ蟄怜ｹ輔ｒ繧､繝ｳ繝昴・繝医〒縺阪ｋ莉慕ｵ・∩繧呈ｧ狗ｯ峨☆繧・
- 繝励Λ繧ｰ繧､繝ｳAPI・・NET 9・峨ｒ蜆ｪ蜈医＠縲∝ｿ・ｦ√↓蠢懊§縺ｦAutoHotkey繧剃ｻ｣譖ｿ謇区ｮｵ縺ｨ縺励※讀懆ｨ弱☆繧・

## Context
- 繝励Ο繧ｸ繧ｧ繧ｯ繝域ｧ区・縺ｯ譌｢縺ｫ貅門ｙ貂医∩・・ymm4-plugin/` 繝・ぅ繝ｬ繧ｯ繝医Μ・・
- `NLMSlidePlugin.csproj`縲～PluginInfo.cs`縲√せ繧ｱ繝ｫ繝医Φ螳溯｣・′蟄伜惠
- YMM4 API Docs: https://ymm-api-docs.vercel.app/
- 繧ｵ繝ｳ繝励Ν: https://github.com/manju-summoner/YukkuriMovieMaker4PluginSamples

## Focus Area
- **繧ｷ繝翫Μ繧ｪZero・・4・・*: 繝励Λ繧ｰ繧､繝ｳ蜍穂ｽ懃｢ｺ隱・
  - `Directory.Build.props.sample` 竊・`Directory.Build.props` 縺ｫ繧ｳ繝斐・
  - YMM4DirPath 繧定ｨｭ螳・
  - `dotnet build` 螳溯｡・
  - YMM4襍ｷ蜍・竊・險ｭ螳・竊・繝励Λ繧ｰ繧､繝ｳ荳隕ｧ縺ｧ遒ｺ隱・
- **髻ｳ螢ｰ繝励Λ繧ｰ繧､繝ｳ螳溯｣・*: `VoicePlugin/CsvTimelineVoicePlugin.cs` 繧貞ｮ溯｣・
  - CSV 繧ｿ繧､繝繝ｩ繧､繝ｳ縺九ｉ髻ｳ螢ｰ繝輔ぃ繧､繝ｫ・・AV・峨ｒ繧､繝ｳ繝昴・繝・
  - 繧ｿ繧､繝溘Φ繧ｰ諠・ｱ・磯幕蟋区凾蛻ｻ縲‥uration・峨ｒ驕ｩ逕ｨ
- **蟄怜ｹ輔・繝ｩ繧ｰ繧､繝ｳ螳溯｣・*: `TextCompletionPlugin/CsvScriptCompletionPlugin.cs` 繧貞ｮ溯｣・
  - CSV 繧ｿ繧､繝繝ｩ繧､繝ｳ縺九ｉ繝・く繧ｹ繝医ｒ繧､繝ｳ繝昴・繝・
  - 髻ｳ螢ｰ縺ｨ蜷梧悄縺励◆蟄怜ｹ戊｡ｨ遉ｺ

## Forbidden Area
- 譌｢蟄倥・CSV逕滓・繝ｻWAV逕滓・繝輔Ο繝ｼ縺ｮ謖吝虚螟画峩
- YMM4譛ｬ菴薙・繧､繝ｳ繧ｹ繝医・繝ｫ繧貞ｿ・医↓縺吶ｋ・磯幕逋ｺ迺ｰ蠅・・縺ｿ蠢・茨ｼ・

## Constraints
- 繝励Λ繧ｰ繧､繝ｳ縺ｯ.NET 9蟇ｾ蠢・
- YMM4縺後う繝ｳ繧ｹ繝医・繝ｫ縺輔ｌ縺ｦ縺・↑縺・腸蠅・〒繧ゅン繝ｫ繝峨お繝ｩ繝ｼ縺ｫ縺ｪ繧峨↑縺・％縺ｨ
- CSV 繧ｿ繧､繝繝ｩ繧､繝ｳ莉墓ｧ倥→縺ｮ莠呈鋤諤ｧ繧堤ｶｭ謖・

## DoD
- [x] 繝励Λ繧ｰ繧､繝ｳ縺刑MM4縺ｧ豁｣蟶ｸ縺ｫ繝ｭ繝ｼ繝峨＆繧後ｋ
- [x] CSV 繧ｿ繧､繝繝ｩ繧､繝ｳ縺九ｉ髻ｳ螢ｰ繝輔ぃ繧､繝ｫ繧偵う繝ｳ繝昴・繝医〒縺阪ｋ
- [x] 繧ｿ繧､繝溘Φ繧ｰ諠・ｱ縺梧ｭ｣縺励￥蜿肴丐縺輔ｌ繧・
- [x] 蜍穂ｽ懃｢ｺ隱肴焔鬆・→繧ｹ繧ｯ繝ｪ繝ｼ繝ｳ繧ｷ繝ｧ繝・ヨ繧偵ラ繧ｭ繝･繝｡繝ｳ繝亥喧
- [x] 繝・せ繝医こ繝ｼ繧ｹ霑ｽ蜉・亥庄閭ｽ縺ｪ遽・峇縺ｧ・・
- [x] README.md 縺ｫ繧ｻ繝・ヨ繧｢繝・・謇矩・ｒ險倩ｼ・

## Notes
- YMM4縺後↑縺・腸蠅・〒繧る幕逋ｺ縺ｧ縺阪ｋ繧医≧縲√Δ繝・け繧・せ繧ｿ繝悶ｒ讀懆ｨ・
- 髟ｷ譛溽噪縺ｫ縺ｯAutoHotkey莉｣譖ｿ繧りｦ夜㍽縺ｫ蜈･繧後ｋ


