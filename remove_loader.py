import re
import glob

files = glob.glob('f:/project/StayZen/templates/**/*.html', recursive=True)

script_min_pattern = re.compile(r'<script>\s*\(\s*function\s*\(\)\s*\{\s*var\s*l\s*=\s*document\.getElementById\([\'\"]sz-loader[\'\"]\)[\s\S]*?\}\(\)\);\s*</script>', re.DOTALL)

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    content = script_min_pattern.sub('', content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'Updated {filepath}')
