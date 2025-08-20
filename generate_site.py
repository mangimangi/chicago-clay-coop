import json
import os
import re

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


def load_json(filename):
    with open(f'''json/{filename}''', 'r', encoding='utf-8') as f:
        return json.load(f)

def format_date(date_str, short=False):
    fmt = '%A, %B %-d'
    if short:
       fmt = '%B %-d'

    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        dt = dt.strftime(fmt)
        return dt
    except:
        return date_str

def get_event_date(event):
    date = event.get('date')
    dates = event.get('dates')

    if dates:
        return f'''{format_date(min(dates), short=True) + "–" + format_date(max(dates), short=True)}'''
    else:
        return format_date(date)

def slugify(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def is_payment_link(url, domains=["stripe.com"]):
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc.lower()
        
        for domain in domains:
            domain = domain.lower()
            if hostname == domain or hostname.endswith('.' + domain):
                return True
        return False
    except:
        return False

def get_cta_text(link):
  if is_payment_link(link):
    return "Register"
  else:
    return "Learn More"

def header(page):
    home = load_json('home.json')
    logo = home.get('thumbnail')

    def nav(nav_class, page):
      return f'''<nav class="{nav_class}">
        <ul>
          <li><a href="/index.html" class={"active" if page == "home" else ""}>Home</a></li>
          <li><a href="/about.html" class={"active" if page == "about" else ""}>About</a></li>
          <li><a href="/visit.html" class={"active" if page == "visit" else ""}>Visit</a></li>
          <li><a href="/schedule.html" class={"active" if page in ["schedule", "event"] else  ""}>Schedule</a></li>
          <li><a href="/members.html" class={"active" if page in ["members", "member"] else ""}>Members</a></li>
        </ul>
      </nav>'''

    return f'''
      <header>
          <div class="logo-thumb"><a href="/index.html"><img src="{logo}" alt="Logo" /></a></div>
          {nav(nav_class="desktop-nav", page=page)}
          <details class="mobile-nav">
            <summary class="hamburger-menu">
              <i class="fa-solid fa-bars"></i>
            </summary>
            {nav(nav_class="mobile-nav-content", page=page)}
          </details>
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

def get_events(sort=True, upcoming=True, past=False, expand=False):
    events = load_json('events.json')

    if expand:
        expanded = []
        for event in events:
            if 'dates' in event:
                # Create separate event for each date
                for date_str in event['dates']:
                    copy = event.copy()
                    copy['date'] = date_str

                    expanded.append(copy)
            else:
                expanded.append(event)
        events = expanded
    else:
        for event in events:
            if event.get('dates') and not event.get('date'):
                event["date"] = min(event["dates"])

    if sort:
        events.sort(key=lambda e: datetime.strptime(e['date'], '%Y-%m-%d') if 'date' in e else datetime.max)

    if upcoming:
        events = [e for e in events if datetime.strptime(e['date'], "%Y-%m-%d").date() >= date.today()]
    elif past:
        events = [e for e in events if datetime.strptime(c['date'], "%Y-%m-%d").date() < date.today()]

    return events

def render_event(event):
    title = event.get('name', '')
    instructor = event.get('instructor', '')
    description = event.get('description', '')
    date = get_event_date(event)
    time = event.get('time', '')
    cost = f"""${event.get('cost')}""" if event.get('cost') else "Free"
    requirements = event.get('requirements', 'Open to All')
    image = event.get('image', '')
    link = event.get('link')

    slug = f"{slugify(title)}-{event.get('date')}"
    page_path = Path("event") / f"{slug}.html"

    # Start details row
    details = f"""<div class='event-details'>
    <div class="event-detail">
        <i class="fa-light fa-dollar-sign"></i>
        <div class="event-detail-text">{cost}</div>
    </div>
    """

    if date or time:
        details += f"""
        <div class="event-detail">
            <i class="fa-regular fa-calendar"></i>
            <div class="event-detail-text">{time + '<br>' + date}</div>
        </div>
        """
    details += f"""
    <div class="event-detail">
        <i class="fa-solid fa-people-group"></i>
        <div class="event-detail-text">{requirements}</div>
    </div>
    </div>
    """

    # Load visit data for collapsible sections
    visit = load_json('visit.json')
    
    # Helper to render collapsible sections
    def render_collapsible_section(title, icon, section_data, list_details, cta=None):
        lists = ''
        for key, (sub_icon, sub_label) in list_details.items():
            if key in section_data:
                items = ''.join(f'<li>{item}</li>' for item in section_data[key])
                lists += f'''
                    <h4><i class="{sub_icon}"></i>{sub_label}</h4>
                    <ul>{items}</ul>
                '''
        
        if cta and section_data.get("link"):
            cta_btn = f'''<a href="{section_data.get("link")}" class="cta-btn">{cta}</a>'''
        else:
            cta_btn = ""
        
        return f'''
        <details class="collapsible-section">
            <summary><i class="{icon}"></i>{title}</summary>
            <div class="collapsible-content">
                {lists}
                {cta_btn}
            </div>
        </details>
        '''

    # Generate collapsible sections
    collapsible_sections = ""
    
    # Directions section
    if visit.get('directions'):
        collapsible_sections += render_collapsible_section(
            "Directions",
            "fa-solid fa-route",
            visit.get('directions', {}),
            {
                "transit": ("fa-solid fa-train-subway", "Transit"),
                "biking": ("fa-solid fa-bicycle", "Bike"),
                "driving": ("fa-solid fa-car", "Car")
            },
            "Get Directions"
        )

    # What to bring section
    if visit.get('bring'):
        collapsible_sections += render_collapsible_section(
            "What to Bring",
            "fa-solid fa-bottle-water",
            visit.get('bring', {}),
            {
                "yes": ("fa-solid fa-thumbs-up", "Encouraged"),
                "no": ("fa-solid fa-thumbs-down", "NOT Allowed"),
                "tools": ("fa-solid fa-toolbox", "Tools")
            },
            "Purchase Here"
        )

    # Nearby section
    if visit.get('nearby'):
        collapsible_sections += render_collapsible_section(
            "What's Nearby",
            "fa-solid fa-map-location-dot",
            visit.get('nearby', {}),
            {
                "cafes": ("fa-solid fa-mug-hot", "Cafes"),
                "food": ("fa-solid fa-utensils", "Food"),
                "bars": ("fa-solid fa-champagne-glasses", "Bars")
            }
        )

    # Share section (looks like collapsible but triggers SMS)
    event_url = f"https://ccc.quest/event/{slug}.html" 
    share_message = f"{event_url} Check out {title} at the Chicago Clay Co-Op!"
    sms_url = f"sms:?body={share_message.replace(' ', '%20').replace('!', '%21').replace('-', '%2D')}"
    
    collapsible_sections += f'''
    <a href="{sms_url}" class="share-section">
        <i class="fa-solid fa-user-plus"></i>Share With A Friend
    </a>
    '''

    cta = ""
    if link:
      cta = f"""<a href="{link}" class="cta-btn">{get_cta_text(link)}</a>"""
        

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <link rel="stylesheet" href="../styles.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("event")}
<main>
  <section class="page-details">
    <div class="details-image">
      <img src="{image}" alt="{title}" />
    </div>
    <div class="details-text">
      <h1 class="details-title">{title}</h1>
      <h3>{f"with {instructor}" if instructor else ""}</h3>
      {details}
      <p class="details-description">{description}</p>
      {cta}
    </div>
  </section>
  
  <section class="event-collapsible-sections">
    {collapsible_sections}
  </section>
</main>
{footer()}
</body>
</html>
"""
    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(content)

def render_event_card(e):
    cost = f"${e['cost']}" if e.get('cost') else '&nbsp;'
    instructor = f"w/ {e['instructor']}" if e.get('instructor') else '&nbsp;'
    slug = f"{slugify(e['name'])}-{e.get('date')}"
    detail_link = f"event/{slug}.html"

    link = e.get('link')
    cta = ""
    if link:
        cta = f"""<a href="{link}" class="cta-btn card-btn">{get_cta_text(link)}</a>"""

    return f'''
        <div class="card">
          <a href="{detail_link}"><img src="{e.get('image', '')}" alt="{e.get('name', '')}" /></a>
          <div class="card-content">
            <h3>{e.get('name', '')}</h3>
            <p>{instructor}</p>
            <p>{e.get('time', '') + '<br>' + get_event_date(e)}</p>
            <p>{cost}</p>
          </div>
          <div class="card-btn-row">
            <a href="{detail_link}" class="cta-btn card-btn details-btn">Details</a>
            {cta}
          </div>
        </div>
    '''

def render_member(member):
    name = member.get('name', '')
    image = member.get('image', '')
    statement = member.get('statement', '')

    slug = slugify(name)
    page_path = Path("member") / f"{slug}.html"

    links = render_member_links(member)

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{name}</title>
  <link rel="stylesheet" href="../styles.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("members")}
<main>
  <section class="page-details">
    <div class="details-image">
      <img src="{image}" alt="{name}" />
    </div>
    <div class="details-text">
      <h1 class="details-title">
        {name}
        <div class="details-links">{links}</div>
      </h1>
      <p class="details-description">{statement}</p>
    </div>
  </section>
</main>
{footer()}
</body>
</html>
"""

    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(content)

def render_member_links(member):
    instagram = member.get('instagram')
    website = member.get('website')

    if instagram and website:
        return f'''
            <div class="card-links">
                <a href="{instagram}" target="_blank" class="card-link half">
                    <i class="fa-brands fa-instagram"></i>
                </a>
                <a href="{website}" target="_blank" class="card-link half">
                    <i class="fa-solid fa-link"></i>
                </a>
            </div>
        '''
    elif instagram:
        return f'''
            <div class="card-links">
                <a href="{instagram}" target="_blank" class="card-link full">
                    <i class="fa-brands fa-instagram"></i>
                </a>
            </div>
        '''
    elif website:
        return f'''
            <div class="card-links">
                <a href="{website}" target="_blank" class="card-link full">
                    <i class="fa-solid fa-link"></i>
                </a>
            </div>
        '''


def render_home():
    home = load_json('home.json')
    testimonials = home.get('testimonials', [])

    events = get_events()
    upcoming = events[:3]

    title_with_br = home.get('title', '').replace('\\n', '<br>')

    upcoming_cards = ''
    for e in upcoming:
        upcoming_cards += render_event_card(e)

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
  <section class="page-details home-page-details">
    <div class="details-text">
      <h1 class="details-title">{title_with_br}</h1>
      <p class="details-description home">{home.get('description')}</p>
      <a href="schedule.html" class="cta-btn">Schedule of Events</a>
    </div>
    <div class="details-image">
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

def render_about():
    about = load_json('about.json')

    sections = '\n'.join(list(map(
      lambda section: f'''
        <section class="page-details home-page-details">
          <div class="details-text">
            <h1 class="details-title">{section.get('title')}</h1>
            <p class="details-description">{section.get('description')}</p>
            {f"""<a href="{section.get('link')}" class="cta-btn">{section.get('cta')}</a>""" if (section.get('link') and section.get('cta')) else ""}
          </div>
          <div class="details-image">
            <img src="{section.get('image')}" alt="Studio image" />
          </div>
        </section>
      ''',
      about.get('sections', [])
    )))

    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>About</title>
<link rel="stylesheet" href="styles.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("about")}
<main>
  {sections}
</main>
{footer()}
</body>
</html>
'''

    with open('about.html', 'w', encoding='utf-8') as f:
        f.write(content)

def render_visit():
    visit = load_json('visit.json')

    # Top carousel of images
    image_carousel = ""
    #''.join(
    #    f'<div class="carousel-image"><img src="{img}" alt="Visit image" /></div>'
    #    for img in visit.get('images', [])
    #)

    # Helper to render a details section with image + bullet lists
    def render_section(title, icon, section_data, list_details, cta=None):
        image = ''
        if section_data.get('map'):
            image = f'''<iframe src="{section_data.get('map')}" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>'''
        elif section_data.get('image'):
            image = f'''<img src="{section_data.get('image')}" alt="{title}" />'''
        
        lists = ''
        for key, (sub_icon, sub_label) in list_details.items():
            if key in section_data:
                items = ''.join(f'<li>{item}</li>' for item in section_data[key])
                lists += f'''
                    <h4><i class="{sub_icon}"></i>{sub_label}</h4>
                    <ul>{items}</ul>
                '''

        if cta and section_data.get("link"):
            cta = f'''<a href="{section_data.get("link")}" class="cta-btn">{cta}</a>'''
        else:
            cta = ""

        return f'''
        <section class="page-details">
          <div class="details-image">
            {image}
          </div>
          <div class="details-text">
            <h2><i class="{icon}"></i>{title}</h2>
            {lists}
            {cta}
          </div>
        </section>
        '''

    # Directions section
    directions = render_section(
        "Directions",
        "fa-solid fa-route",
        visit.get('directions', {}),
        {
            "transit": ("fa-solid fa-train-subway", "Transit"),
            "biking": ("fa-solid fa-bicycle", "Bike"),
            "driving": ("fa-solid fa-car", "Car")
        },
        "Get Directions"
    )

    # What to bring section
    bring = render_section(
        "What to Bring",
        "fa-solid fa-bottle-water",
        visit.get('bring', {}),
        {
            "yes": ("fa-solid fa-thumbs-up", "Encouraged"),
            "no": ("fa-solid fa-thumbs-down", "NOT Allowed"),
            "tools": ("fa-solid fa-toolbox", "Tools")
        },
        "Purchase Here"
    )

    # Nearby  section
    nearby = render_section(
        "What's Nearby",
        "fa-solid fa-map-location-dot",
        visit.get('nearby', {}),
        {
            "cafes": ("fa-solid fa-mug-hot", "Cafes"),
            "food": ("fa-solid fa-utensils", "Food"),
            "bars": ("fa-solid fa-champagne-glasses", "Bars")
        }
    )

    content = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Visit</title>
<link rel="stylesheet" href="styles.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("visit")}
<main>
  <h1>Visit</h1>
  <div class="carousel visit-carousel">
    {image_carousel}
  </div>
  {directions}
  {bring}
  {nearby}
</main>
{footer()}
</body>
</html>
'''

    with open('visit.html', 'w', encoding='utf-8') as f:
        f.write(content)


def render_schedule():
    # Group events by month
    grouped = {}
    for e in get_events():
        render_event(e)

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
        event_cards = ''.join([render_event_card(e) for e in events_in_month])
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
<title>Schedule</title>
<link rel="stylesheet" href="styles.css" />
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header("schedule")}
<main>
  <h1>Schedule of Events</h1>
  <div class="month-nav">
    {month_nav}
  </div>
  {content_blocks}
</main>
{footer()}
</body>
</html>
'''

    with open('schedule.html', 'w', encoding='utf-8') as f:
        f.write(content)

def render_members():
    members = load_json('members.json')

    cards = ''
    for m in members:
        render_member(m)

        links = render_member_links(m)
        slug = slugify(m.get("name", ""))
        profile_link = f"member/{slug}.html"

        cards += f'''
            <div class="card">
              <a href="{profile_link}"><img src="{m.get('image', '')}" alt="{m.get('name', '')}" /></a>
              <div class="card-content">
                <h3>{m.get('name', '')}</h3>
                <div class="card-links">
                  {links}
                </div>
              </div>
              <a href="{profile_link}" class="cta-btn card-btn">Profile</a>
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
    render_about()
    render_visit()
    render_schedule()
    render_members()


if __name__ == '__main__':
    main()

