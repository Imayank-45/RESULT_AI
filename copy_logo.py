import os

src = r"C:\Users\mayan\.gemini\antigravity-ide\brain\14285cfe-ce6a-4f14-b649-95f140bfe626\media__1784561737544.jpg"
dst_png = r"frontend\public\logo.png"
dst_jpg = r"frontend\public\logo.jpg"
dst_src = r"frontend\src\assets\logo.png"

os.makedirs(os.path.dirname(dst_src), exist_ok=True)

with open(src, 'rb') as f_in:
    data = f_in.read()

with open(dst_png, 'wb') as f_out:
    f_out.write(data)

with open(dst_jpg, 'wb') as f_out:
    f_out.write(data)

with open(dst_src, 'wb') as f_out:
    f_out.write(data)

print(f"SUCCESS: Written {len(data)} bytes to logo files!")
