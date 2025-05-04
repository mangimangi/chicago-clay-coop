import json
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
import calendar

TEMPLATE_HEADER = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Quicksand&family=Solway:wght@700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header>
<a href="index.html" class="logo-link">
  <img src="https://file-the-coop.tor1.cdn.digitaloceanspaces.com/logo.png" alt="Logo">
</a>
<nav>
<a href="index.html">Home</a>
<a href="about.html">About</a>
<a href="workshops.html">Workshops</a>
<a href="members.html">Members</a>
</nav>
</header>
<div class="container">
<div class="page-header">
<h1>{title}</h1>
{button}
</div>
'''

TEMPLATE_FOOTER = '''
</div>
<footer class="site-footer">
  &copy; 2025 Chicago Clay Co-operative
</footer>
</body>
</html>
'''

def generate_members_html(members):
    html = TEMPLATE_HEADER.format(title="Members", button=f'''<a class="button" href="#">Apply Now</a>''')
    for member in members:
        links_html = ''
        if 'shop' in member:
            links_html += f'<a href="{member["shop"]}" target="_blank" title="Shop"><i class="fa-solid fa-cart-shopping"></i></a> '
        if 'instagram' in member:
            links_html += f'<a href="{member["instagram"]}" target="_blank" title="Instagram"><i class="fa-brands fa-instagram"></i></a> '
        if 'website' in member:
            links_html += f'<a href="{member["website"]}" target="_blank" title="Website"><i class="fa-solid fa-link"></i></a>'

        html += f'''
        <div class="member" id="{member['name'].lower().replace(' ', '-')}">
            <div class="member-left">
                <img src="{member['image']}" alt="{member['name']}">
            </div>
            <div class="member-right">
              <div class="member-header">
                <h2>{member['name']}</h2>
                <div class="member-links">{links_html}</div>
              </div>
              <p>{member['statement']}</p>
            </div>
        </div>
        '''
    html += TEMPLATE_FOOTER
    Path("members.html").write_text(html)

def highlight_class(date_str, workshop_dates):
    return "highlight" if date_str in workshop_dates else ""

def generate_month_calendar(year, month, workshop_dates):
    cal = calendar.Calendar(firstweekday=6)  # 6 = Sunday
    month_name = calendar.month_name[month]
    html = f'<h2>{month_name} {year}</h2>'
    html += '<table><thead><tr>' + ''.join(f'<th>{day}</th>' for day in ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']) + '</tr></thead><tbody>'

    weeks = cal.monthdayscalendar(year, month)
    for week in weeks:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td></td>'
            else:
                date_str = date(year, month, day).isoformat()
                cls = highlight_class(date_str, workshop_dates)
                html += f'<td class="{cls}"><a href="#ws-{date_str}">{day}</a></td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html

def generate_workshops_html(workshops):
    today = date.today()
    workshops = [w for w in workshops if datetime.strptime(w['date'], "%Y-%m-%d").date() >= today]
    workshops.sort(key=lambda w: datetime.strptime(w['date'], "%Y-%m-%d"))
    workshop_dates = {ws['date'] for ws in workshops}
    html = TEMPLATE_HEADER.format(title="Workshops", button="")
    for ws in workshops:
      html += f'''
        <div class="workshop" id="ws-{ws['date']}">
            <div class="workshop-left">
                <img src="{ws['image']}" alt="{ws['name']}">
            </div>
            <div class="workshop-right">
                <div class="workshop-header">
                    <h2>{ws['name']}</h2>
                    <a class="button" href="{ws['link']}" target="_blank">Book</a>
                </div>
                <div class="workshop-details">
                  <h4>{datetime.strptime(ws['date'], "%Y-%m-%d").strftime("%A, %B %-d") + " at " + ws['time']}</h4>
                  {f"<h4><a href='members.html#{ws.get('instructor', '').lower().replace(' ', '-')}'>{'&nbsp;&nbsp;w/ ' + ws['instructor']}</a></h4>" if ws.get('instructor') else ""}
                </div>
                <p>{ws['description']}</p>
            </div>
        </div>
      '''

    html += f'''<div class="calendar">'''
    html += generate_month_calendar(today.year, today.month, workshop_dates)
    next_month = today.replace(day=28) + timedelta(days=4)
    html += generate_month_calendar(next_month.year, next_month.month, workshop_dates)
    html += '</div>'
    html += TEMPLATE_FOOTER
    Path("workshops.html").write_text(html)

def generate_index_html():
    html = TEMPLATE_HEADER.format(title="", button="")
    html += f'''
      <div class='home'>
        <img src="https://images.pexels.com/photos/3094036/pexels-photo-3094036.jpeg" alt="The Coop">
      </div>
    '''
    html += TEMPLATE_FOOTER
    Path("index.html").write_text(html)

def generate_about_html():
    html = TEMPLATE_HEADER.format(title="About", button="")
    html += '<p>This is a static website generated from JSON data for members and workshops.</p>'
    html += TEMPLATE_FOOTER
    Path("about.html").write_text(html)

if __name__ == "__main__":
    members_file = sys.argv[1]
    workshops_file = sys.argv[2]

    members = json.loads(Path(members_file).read_text())
    workshops = json.loads(Path(workshops_file).read_text())

    generate_members_html(members)
    generate_workshops_html(workshops)
    generate_index_html()
    generate_about_html()

