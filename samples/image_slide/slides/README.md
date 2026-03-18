# Test Slide Images

SP-035 統合実機テスト用のプレースホルダー画像。
`.gitignore` で *.png が除外されているため、ローカルで生成する。

## 生成方法

```bash
cd NLMandSlideVideoGenerator
.\venv\Scripts\python.exe -c "
from PIL import Image, ImageDraw
colors = [(60,80,120),(80,120,60),(120,60,80)]
for i,c in enumerate(colors,1):
    img = Image.new('RGB',(1920,1080),c)
    d = ImageDraw.Draw(img)
    d.text((860,530),f'slide_{i:04d}',fill=(255,255,255))
    img.save(f'samples/image_slide/slides/slide_{i:04d}.png')
"
```

## 必要な画像

- `slide_0001.png` (1920x1080)
- `slide_0002.png` (1920x1080)
- `slide_0003.png` (1920x1080)

`e2e_baseline_test.csv` が相対パス `slides/slide_XXXX.png` で参照する。
