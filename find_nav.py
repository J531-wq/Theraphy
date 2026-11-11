content = open('therapy_site/core/templates/core/blog_detail.html', encoding='utf-8').read()
idx = content.find('<nav')
print("FOUND at", idx)
print(content[idx:idx+1500])
