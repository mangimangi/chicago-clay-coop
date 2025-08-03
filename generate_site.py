import json
from datetime import date, datetime

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except:
        return date_str

def header(page):
    home = load_json('home.json')
    logo = home.get('thumbnail')

    return f'''
      <header>
          <div class="logo-thumb"><a href="index.html"><img src="{logo}" alt="Logo" /></a></div>
          <nav>
            <ul>
              <li><a href="index.html" class={"active" if page == "home" else ""}>Home</a></li>
              <li><a href="events.html" class={"active" if page == "events" else  ""}>Events</a></li>
              <li><a href="members.html" class={"active" if page == "members" else ""}>Members</a></li>
            </ul>
          </nav>
      </header>
    '''

def footer():
    home = load_json('home.json')

    return f'''
      <footer>
        <div class="footer-links">
          <a href="{home.get('instagram', '#')}" target="_blank"><i class="fa-brands fa-instagram"></i></a>
          <a href="mailto:{home.get('email', '#')}"><i class="fa-solid fa-envelope"></i></a>
          <a href="tel:{home.get('phone', '#')}"><i class="fa-solid fa-phone"></i></a>
        </div>
        <div class="footer-copy">&copy; 2025 Chicago Clay Co-Op</div>
      </footer>
    '''

def get_combined_events():
    events = load_json('events.json')
    workshops = load_json('workshops.json')
    combined = events + workshops

    combined.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d') if 'date' in x else datetime.max)
    future = [c for c in combined if datetime.strptime(c['date'], "%Y-%m-%d").date() >= date.today()]

    return future 

def get_event_card(e):
    cost = f"${e['cost']}" if e.get('cost') else '&nbsp;'
    instructor = f"w/ {e['instructor']}" if e.get('instructor') else '&nbsp;'
    return f'''
        <div class="card">
          <img src="{e.get('image', '')}" alt="{e.get('name', '')}" />
          <div class="card-content">
            <h3>{e.get('name', '')}</h3>
            <p>{instructor}</p>
            <p>{format_date(e.get('date', ''))}</p>
            <p>{cost}</p>
          </div>
          <a href="{e.get('link', '#')}" class="cta-btn card-btn">Register</a>
        </div>
    '''

def render_home():
    home = load_json('home.json')
    testimonials = home.get('testimonials', [])
    logo = home.get('thumbnail', 'logo.png')

    events = get_combined_events()
    upcoming = events[:3]

    title_with_br = home.get('title', '').replace('\\n', '<br>')

    upcoming_cards = ''
    for e in upcoming:
        upcoming_cards += get_event_card(e)

    testimonial_cards = ''
    for t in testimonials[:2]:
        testimonial_cards += f'''
    <div class="testimonial-card">
      <img src="{t.get('image', '')}" alt="Testimonial Background">
      <div class="testimonial-bubble">
        <p>"{t.get('text', '')}"
          <br>
          <strong>- {t.get('name', '')}, {t.get('location', '')}</strong>
        </p>
      </div>
    </div>
    '''

    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Chicago Clay Co-Op</title>
<link rel="stylesheet" href="styles.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("home")}
<main>
  <section class="home-top">
    <div class="home-text">
      <h1 class="home-title">{title_with_br}</h1>
      <p class="home-description">{home.get('description')}</p>
      <a href="events.html" class="cta-btn">Schedule of Events</a>
    </div>
    <div class="home-image">
      <img src="{home.get('image')}" alt="Studio image" />
    </div>
  </section>
  <section>
    <h2>Upcoming Events</h2>
    <div class="carousel">
      {upcoming_cards}
    </div>
  </section>
  <section>
    <h2>Testimonials</h2>
    <div class="card-grid testimonial-grid">
      {testimonial_cards}
    </div>
  </section>
</main>
{footer()}
</body>
</html>
'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)

def render_events():
    home = load_json('home.json')
    logo = home.get('thumbnail', 'logo.png')
    events = get_combined_events()

    # Group events by month
    grouped = {}
    for e in events:
        if 'date' not in e:
            continue
        dt = datetime.strptime(e['date'], "%Y-%m-%d")
        month_label = dt.strftime('%B')
        grouped.setdefault(month_label, []).append(e)

    month_nav = ''
    for month, _ in grouped.items():
        short_month = datetime.strptime(month, "%B").strftime("%b")
        month_nav += f'<a href="#{month.lower()}" class="month-link">{short_month}</a>\n'

    # Build the content
    content_blocks = ''
    for month, events_in_month in grouped.items():
        event_cards = ''.join([get_event_card(e) for e in events_in_month])
        content_blocks += f'''
        <h2 id="{month.lower()}" class="month-header">{month}</h2>
        <section class="card-grid">
          {event_cards}
        </section>
        '''

    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Events</title>
<link rel="stylesheet" href="styles.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("events")}
<main>
  <h1>Events</h1>
  <div class="month-nav">
    {month_nav}
  </div>
  {content_blocks}
</main>
{footer()}
</body>
</html>
'''

    with open('events.html', 'w', encoding='utf-8') as f:
        f.write(content)

def render_members():
    members = load_json('members.json')

    cards = ''
    for m in members:
        links = ''
        if m.get("instagram") and m.get("website"):
            links = f'''
                <div class="card-links">
                    <a href="{m['instagram']}" target="_blank" class="card-link half">
                        <i class="fa-brands fa-instagram"></i>
                    </a>
                    <a href="{m['website']}" target="_blank" class="card-link half">
                        <i class="fa-solid fa-link"></i>
                    </a>
                </div>
            '''
        elif m.get("instagram"):
            links = f'''
                <div class="card-links">
                    <a href="{m['instagram']}" target="_blank" class="card-link full">
                        <i class="fa-brands fa-instagram"></i>
                    </a>
                </div>
            '''
        elif m.get("website"):
            links = f'''
                <div class="card-links">
                    <a href="{m['website']}" target="_blank" class="card-link full">
                        <i class="fa-solid fa-link"></i>
                    </a>
                </div>
            '''


        cards += f'''
            <div class="card">
              <img src="{m.get('image', '')}" alt="{m.get('name', '')}" />
              <div class="card-content">
                <h3>{m.get('name', '')}</h3>
                <div class="card-links">
                  {links}
                </div>
              </div>
              <a href="{m.get('profile_link', '#')}" class="cta-btn card-btn">Profile</a>
            </div>
        '''

    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Members</title>
<link rel="stylesheet" href="styles.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("members")}
<main>
  <h1>Members</h1>
  <section class="card-grid">
    {cards}
  </section>
</main>
{footer()}
</body>
</html>
'''
    with open('members.html', 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    render_home()
    render_events()
    render_members()

if __name__ == '__main__':
    main()

