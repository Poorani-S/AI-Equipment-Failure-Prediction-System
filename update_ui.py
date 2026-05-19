import re

with open('static/js/enhanced-ui.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace container insertions
old_insertion = "const container = document.querySelector('.dashboard-container') || document.body;\n    container.insertAdjacentHTML('beforeend',"
new_insertion = "const header = document.querySelector('.dashboard-header');\n    if (header) { header.insertAdjacentHTML('afterend',"

content = content.replace(old_insertion, new_insertion)

content = content.replace("anomalyHTML);", "anomalyHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', anomalyHTML); }")
content = content.replace("comparisonHTML);", "comparisonHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', comparisonHTML); }")
content = content.replace("costHTML);", "costHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', costHTML); }")
content = content.replace("perfHTML);", "perfHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', perfHTML); }")
content = content.replace("sensorHTML);", "sensorHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', sensorHTML); }")
content = content.replace("alertHTML);", "alertHTML); } else { (document.querySelector('.dashboard-container') || document.body).insertAdjacentHTML('afterbegin', alertHTML); }")

# Update AI Chat Greeting
content = content.replace('<div class="chat-messages" id="chatMessages"></div>', '<div class="chat-messages" id="chatMessages">\n                <div class="chat-message chat-ai">Hello I am Prediction Assistant, how can I help you?</div>\n            </div>')

# Fix Scroll Into View
pattern = r"(panel\.style\.display = panel\.style\.display === 'none' \? 'block' : 'none';\s*if \(panel\.style\.display === 'block'\) \{)"
replacement = r"\1\n                panel.scrollIntoView({ behavior: 'smooth', block: 'start' });"
content = re.sub(pattern, replacement, content)

with open('static/js/enhanced-ui.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updates applied to enhanced-ui.js successfully.")
