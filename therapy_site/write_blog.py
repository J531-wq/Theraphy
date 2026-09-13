import io
p = 'core/templates/core/blog_list.html'
head = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blog — MyTherapyDoctor</title>
{% load static %}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0">
<link rel="alternate" type="application/rss+xml" title="MyTherapyDoctor Blog" href="https://mytherapydoctor.com{% url 'blog_feed' %}">
<meta name="description" content="Mental health insights, wellness tips, therapy advice and success stories from the MyTherapyDoctor journal.">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="https://mytherapydoctor.com/blog/">
<link rel="icon" type="image/png" href="{% static 'core/logo.png' %}">
<meta property="og:type" content="website"><meta property="og:site_name" content="MyTherapyDoctor">
<meta property="og:title" content="Blog — MyTherapyDoctor">
<meta property="og:description" content="Mental health insights, wellness tips, and stories to support your journey.">
<meta property="og:url" content="https://mytherapydoctor.com/blog/">
<meta property="og:image" content="https://mytherapydoctor.com{% static 'core/Social.jpg' %}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Blog — MyTherapyDoctor">
<meta name="twitter:description" content="Mental health insights, wellness tips, and stories to support your journey.">
<style>
'''
io.open(p, 'w', encoding='utf-8').write(head)
print('head written')

