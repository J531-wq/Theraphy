import glob, os
files = glob.glob('therapy_site/core/templates/core/*.html')
for f in sorted(files):
    content = open(f, encoding='utf-8').read()
    has_header = 'site-nav' in content or '<nav' in content or 'header' in content.lower()
    has_footer = 'footer' in content.lower()
    hdr = 'HDR' if has_header else '   '
    ftr = 'FTR' if has_footer else '   '
    print(hdr + ' ' + ftr + ' | ' + os.path.basename(f))
