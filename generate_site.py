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
<link rel="stylesheet" href="https://use.typekit.net/fjf5mmt.css">
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
<a href="events.html">Events</a>
<a href="members.html">Members</a>
<a href="calendar.html">Studio Calendar</a>
</nav>
</header>
<div class="container">
<div class="page-header">
<h1>{title}</h1>
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
    html = TEMPLATE_HEADER.format(title="Members")
    for member in members:
        links_html = ''
        if 'shop' in member:
            links_html += f'<a href="{member["shop"]}" target="_blank" title="Shop"><i class="fa-solid fa-cart-shopping"></i></a> '
        if 'instagram' in member:
            links_html += f'<a href="{member["instagram"]}" target="_blank" title="Instagram"><i class="fa-brands fa-instagram"></i></a> '
        if 'website' in member:
            links_html += f'<a href="{member["website"]}" target="_blank" title="Website"><i class="fa-solid fa-link"></i></a>'

        html += f'''
        <div class="member" id="{make_anchor(member['name'])}">
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

def generate_month_calendar(year, month, workshop_dates, event_dates):
    cal = calendar.Calendar(firstweekday=6)  # 6 = Sunday
    month_name = calendar.month_name[month]
    html = '<div class="month">'
    html += f'<h2>{month_name} {year}</h2>'
    html += '<table><thead><tr>' + ''.join(f'<th>{day}</th>' for day in ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']) + '</tr></thead><tbody>'

    weeks = cal.monthdayscalendar(year, month)
    for week in weeks:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td></td>'
            else:
                date_str = date(year, month, day).isoformat()
                if date_str in workshop_dates:
                  html += f'''<td class="calendar-workshop"><a href="events.html#ws-{date_str}">{day}</a></td>'''
                elif date_str in event_dates:
                  html += f'''<td class="calendar-event"><a href="events.html#e-{date_str}">{day}</a></td>'''
                else:
                  html += f'''<td>{day}</td>'''
        html += '</tr>'
    html += '</tbody></table></div>'
    return html

def generate_calendar(workshops, events):
    html = TEMPLATE_HEADER.format(title="Studio Calendar")

    workshop_dates = {ws['date'] for ws in workshops}
    event_dates = {e['date'] for e in events}
    # Convert dates to (year, month) tuples
    months = sorted({(datetime.strptime(d, "%Y-%m-%d").year, datetime.strptime(d, "%Y-%m-%d").month) for d in workshop_dates | event_dates})
    html += '<div class="calendar">'
    for year, month in months:
        html += generate_month_calendar(year, month, workshop_dates, event_dates)
    html += '</div>'

    html += TEMPLATE_FOOTER
    Path("calendar.html").write_text(html)

def generate_events_html(workshops, events, member_names):
    html = TEMPLATE_HEADER.format(title="Workshops")

    workshops.sort(key=lambda w: datetime.strptime(w['date'], "%Y-%m-%d"))
    for ws in workshops:
      instructor = ws.get('instructor')
      if instructor:
        if instructor in member_names:
          instructor = f"<a href='members.html#{make_anchor(ws.get('instructor', ''))}'>{instructor}</a>"
        else:
          instructor = f"{instructor}"

      html += f'''
        <div class="workshop" id="ws-{ws['date']}">
            <div class="workshop-left">
                <img src="{ws['image']}" alt="{ws['name']}">
            </div>
            <div class="workshop-right">
                <div class="workshop-header">
                    <h2>{ws['name']}</h2>
                </div>
                <div class="workshop-details">
                  {f"<h4>{instructor}</h4>" if instructor else ""}
                  <h4>{datetime.strptime(ws['date'], "%Y-%m-%d").strftime("%A, %B %-d") + " at " + ws['time']}</h4>
                  {f"<h4>${ws['cost']}</h4>" if ws.get('cost') else ""}
                </div>
                <div class="workshop-details workshop-booking">
                  {f'<a class="button" href="{ws.get("link")}" target="_blank">Book</a>' if ws.get("link") else ""}
                </div>
            </div> <!-- close .workshop-right -->
        </div> <!-- close .workshop -->
        <div class="workshop-description">
            <p>{ws['description']}</p>
        </div>
      '''
    
    events.sort(key=lambda e: datetime.strptime(e['date'], "%Y-%m-%d"))
    if events:
      html += "<h1>Events</h1>"

      for event in events:
          event_date = datetime.strptime(event['date'], "%Y-%m-%d").strftime("%A, %B %-d")
          html += f'''
          <div class="event" id="e-{event['date']}">
              <div class="event-left">
                  <img src="{event['image']}" alt="{event['name']}">
              </div>
              <div class="event-right">
                  <div class="event-header">
                      <h2>{event['name']}</h2>
                  </div>
                  <div class="event-details">
                    <h4>{event_date} at {event['time']}</h4>
                  </div>
                  <p>{event['description']}</p>
              </div>
          </div>
          '''
    
    html += TEMPLATE_FOOTER
    Path("events.html").write_text(html)

def generate_home_html(home, upcoming_events):
    upcoming_html = ""
    for event in upcoming_events:
      upcoming_html += f'''
        <a href={event['anchor']}>
          <h3>{event['name']}</h3>
          <p>{datetime.strptime(event['date'], "%Y-%m-%d").strftime("%A, %B %-d") + " at " + event['time']}</p>
        </a>
      '''

    html = TEMPLATE_HEADER.format(title="")
    html += f'''
      <div class='home'>
        <div class='about-left'>
          <img src={home['image']} alt="co-op wide">
        </div>
        <div class='about-right'>
          <div class='upcoming'>
            <h1>Upcoming</h1>
            {upcoming_html}
          </div>
          <h1>About Us</h1>
          <p>{home['text']}</p>
          <div class='cta'>
            <p><a class="button" href="{home['apply']}" target="_blank">Apply for Membership</a></p>
          </div>
          <div class='contact'>
            <h1>Contact</h1>
            <a href="mailto:{home["email"]}" target="_blank" title="Email"><i class="fa-solid fa-envelope"></i>{"&nbsp;&nbsp;" + "ChicagoClayCooperative@gmail.com"}</a>
            <br>
            <a href={home["instagram"]} target="_blank" title="Instagram"><i class="fa-brands fa-instagram"></i>{"&nbsp;&nbsp;" + "@ChicagoClayCooperative"}</a>
            <br>
            <a href="tel:{home['phone'].replace(' ','').replace('(','').replace(')','').replace('-','')}" target="_blank" title="Phone"><i class="fa-solid fa-phone"></i>{"&nbsp;&nbsp;" + home['phone']}</a>
          </div>
        </div>
      </div>
    '''
    html += TEMPLATE_FOOTER
    Path("index.html").write_text(html)

def make_anchor(s):
  return s.lower().replace(' ', '-')

if __name__ == "__main__":
    home_file = sys.argv[1]
    home  = json.loads(Path(home_file).read_text())
    
    members_file = sys.argv[2]
    members = json.loads(Path(members_file).read_text())
    
    workshops_file = sys.argv[3]
    workshops = json.loads(Path(workshops_file).read_text())
    workshops = [w for w in workshops if datetime.strptime(w['date'], "%Y-%m-%d").date() >= date.today()]
    
    events_file = sys.argv[4]
    events = json.loads(Path(events_file).read_text())
    events = [e for e in events if datetime.strptime(e['date'], "%Y-%m-%d").date() >= date.today()]

    generate_members_html(members)
    generate_events_html(workshops, events, {m['name'] for m in members if m.get('name')})
    generate_calendar(workshops, events)
    generate_home_html(home, sorted([{**e, "anchor": f'events.html#e-{e["date"]}'} for e in events] + [{**ws, "anchor": f'events.html#ws-{ws["date"]}'} for ws in workshops], key=lambda item: datetime.strptime(item["date"], "%Y-%m-%d"))[:3])

