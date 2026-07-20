import os
import base64

logo_artifact = r"C:\Users\mayan\.gemini\antigravity-ide\brain\14285cfe-ce6a-4f14-b649-95f140bfe626\media__1784561737544.jpg"
root_dir = os.path.dirname(os.path.abspath(__file__))
public_dir = os.path.join(root_dir, "frontend", "public")
src_assets = os.path.join(root_dir, "frontend", "src", "assets")
dist_dir = os.path.join(root_dir, "frontend", "dist")

for d in [public_dir, src_assets, dist_dir]:
    os.makedirs(d, exist_ok=True)
    with open(logo_artifact, "rb") as f_in:
        data = f_in.read()
    with open(os.path.join(d, "logo.png"), "wb") as f_out:
        f_out.write(data)
    with open(os.path.join(d, "logo.jpg"), "wb") as f_out:
        f_out.write(data)

with open(logo_artifact, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

js_content = f'export const LOGO_BASE64 = "data:image/jpeg;base64,{b64}";\nexport default LOGO_BASE64;\n'

with open(os.path.join(src_assets, "logoData.js"), "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"SUCCESS! Wrote base64 logo ({len(b64)} chars) to {os.path.join(src_assets, 'logoData.js')}")
