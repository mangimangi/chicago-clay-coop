import json
import os
import re

from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

NEWLINE = '\\n'
_JSON_CACHE = {}

def load_json(filename):
    if filename not in _JSON_CACHE:
        with open(f'json/{filename}', 'r', encoding='utf-8') as f:
            _JSON_CACHE[filename] = json.load(f)
    return _JSON_CACHE[filename]

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

def get_cta_text(link, event=True):
    if is_payment_link(link) and event:
        return "Register"
    elif is_payment_link(link):
        return "Buy"
    else:
        return "Learn More"

def get_event_card_data(e):
    day_type = 'weekend' if datetime.strptime(e.get('date', ''), '%Y-%m-%d').weekday() in  [5,6] else 'weekday'

    period = 'unknown'
    match = re.search(r'(\d{1,2})\s*(am|pm)', e.get('time', ''))
    if match:
        hour, ampm = int(match.group(1)), match.group(2)
        if ampm == "am":
            period = 'morning'
        elif hour < 5:
            period = 'afternoon'
        else:
            period = 'evening'
            
    event_type = 'free' if not e.get('cost') else 'class' if e.get('dates') else 'workshop'
    technique = e.get('technique', 'none')

    return f'''data-day-type="{day_type}" data-time-period="{period}" data-event-type="{event_type}" data-technique="{technique}"'''

# Extract common page structure
def build_page_html(title, content, page_type, css_path="styles.css", icon=None):
    if not icon:
        home = load_json('home.json')
        icon = home.get('thumbnail')

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{title}</title>
  <link rel="icon" type="image/png" href={icon}>
  <link rel="stylesheet" href="{css_path}" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />
</head>
<body>
{header(page_type)}
<main>
{content}
</main>
{footer()}
</body>
</html>
'''

def header(page):
    home = load_json('home.json')
    logo = home.get('thumbnail')

    def nav(nav_class, page):
        nav_items = [
            ("home", "/index.html", "Home"),
            ("about", "/about.html", "About"), 
            ("visit", "/visit.html", "Visit"),
            ("schedule", "/schedule.html", "Schedule"),
            ("makers", "/makers.html", "Makers")
        ]
        
        links = []
        for page_key, url, label in nav_items:
            # Handle special cases for active state
            active_pages = {
                "schedule": ["schedule", "event"],
                "makers": ["makers", "maker"],
                "shop": ["shop"]
            }
            is_active = page in active_pages.get(page_key, [page_key])
            active_class = 'class="active"' if is_active else ""
            links.append(f'<li><a href="{url}" {active_class}>{label}</a></li>')
        
        return f'''<nav class="{nav_class}">
        <ul>
          {''.join(links)}
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
          <a href="mailto:{home.get('email', '#')}"><i class="fa-regular fa-envelope"></i></a>
          <a href="tel:{home.get('phone', '#')}"><i class="fa-solid fa-phone"></i></a>
        </div>
        <div class="footer-copy">&copy; 2025 Chicago Clay Co-Op</div>
      </footer>
    '''

def get_events(sort=True, upcoming=True, past=False, expand=False):
    events = load_json('events.json').get('events',[])

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
        events = [e for e in events if datetime.strptime(e['date'], "%Y-%m-%d").date() < date.today()]

    return events

def render_hero(title, image=None):
    if not image:
        return f'''<h1>{title}</h1>'''

    return f'''<div class="hero">
<img src="{image}" alt="Hero Image"/>
  <h1>{title}</h1>
</div>'''

# Extract common detail section rendering  
def render_detail_section(title, icon=None, description=None, lists=None, image=None, iframe=None, link=None, cta_text=None, reverse=False):
    reverse_class = "page-details-reverse" if reverse else ""
    icon = f'<i class="{icon}"></i>' if icon else ""

    return f'''
    <section class="page-details {reverse_class}">
      <div class="details-text">
        <h2 class="details-title">{icon}{title.replace(NEWLINE, '<br>')}</h2>
        {render_detail_section_body(description, lists, image, iframe, link, cta_text)}
      </div>
      {render_detail_media(image, iframe, title)}
    </section>
    '''

def render_detail_section_body(description=None, lists=None, image=None, iframe=None, link=None, cta_text=None):
    description = f'<p class="details-description">{description.replace(NEWLINE, "<br>")}</p>' if description else ""
    lists = render_detail_lists(lists) if lists else ""
    cta = f'<a href="{link}" class="cta-btn">{cta_text}</a>' if link and cta_text else ""
 
    return f'''
        {description}
        {lists}
        {cta}
    '''

def render_detail_lists(lists):
    output= ''

    for l in lists:
      items = ''.join(f'<li>{item}</li>' for item in l.get('items'))
      output += f'''
          <h4><i class="{l.get('icon')}"></i>{l.get('title')}</h4>
          <ul>{items}</ul>
      '''

    return output

def render_detail_media(image, iframe, title):
    media=''

    if iframe:
        media = f'''<iframe src="{iframe}" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>'''
    elif image:
        media = f'''<img src="{image}" alt="{title}" />'''

    return f'''
    <div class="details-media">
        {media}
    </div>
    '''

# Extract collapsible section rendering
def render_collapsible_detail_section(title, icon=None, description=None, lists=None, image=None, iframe=None, link=None, cta_text=None, reverse=False):
    reverse_class = "page-details-reverse" if reverse else ""
    icon = f'<i class="{icon}"></i>' if icon else ""

    return f'''
    <details class="collapsible-section">
        <summary>{icon}<p>{title}</p></summary>
        <div class="collapsible-content page-details {reverse_class}">
            <div class="details-text">
              {render_detail_section_body(description, lists, image, iframe, link, cta_text)}
            </div>
            {render_detail_media(image, iframe, title)}
        </div>
    </details>
    '''

def render_share_section(title, slug):
    url = f"https://ccc.quest/event/{slug}.html" 
    share_message = f"{url} Check out {title} at the Chicago Clay Co-Op!"
    sms_url = f"sms:?body={share_message.replace(' ', '%20').replace('!', '%21').replace('-', '%2D')}"
    
    return f'''
    <a href="{sms_url}" class="share-section">
        <i class="fa-solid fa-user-plus"></i><p>Share With A Friend</p>
    </a>
    '''

def render_shop_share_section(title, slug, item_type):
    url = f"https://ccc.quest/shop/{slug}.html" 
    share_message = f"{url} Check out this {item_type} at the Chicago Clay Co-Op!"
    sms_url = f"sms:?body={share_message.replace(' ', '%20').replace('!', '%21').replace('-', '%2D')}"
    
    return f'''
    <a href="{sms_url}" class="share-section">
        <i class="fa-solid fa-user-plus"></i><p>Share With A Friend</p>
    </a>
    '''

def render_pot_card(pot):
    cost = f"${pot['cost']}" if pot.get('cost') else '&nbsp;'
    artist = f"by {pot['artist']}" if pot.get('artist') else '&nbsp;'
    slug = slugify(f"{pot['title']}-{pot.get('artist', '')}")
    detail_link = f"shop/{slug}.html"

    link = pot.get('link')
    cta = f"""<a href="{link}" class="cta-btn card-btn">{get_cta_text(link, False)}</a>""" if link else ""

    return f'''
        <div class="card">
          <a href="{detail_link}"><img src="{pot.get('image', '')}" alt="{pot.get('title', '')}" /></a>
          <div class="card-content">
            <h3>{pot.get('title', '')}</h3>
            <p>{artist}</p>
            <p>{pot.get('media', '')}</p>
            <p>{pot.get('year', '')}</p>
            <p>{cost}</p>
          </div>
          <div class="card-btn-row">
            <a href="{detail_link}" class="cta-btn card-btn details-btn">Details</a>
            {cta}
          </div>
        </div>
    '''

def render_merch_card(merch):
    cost = f"${merch['cost']}" if merch.get('cost') else '&nbsp;'
    artist = f"by {merch['artist']}" if merch.get('artist') else '&nbsp;'
    slug = slugify(f"{merch['title']}-{merch.get('artist', '')}")
    detail_link = f"shop/{slug}.html"

    link = merch.get('link')
    cta = f"""<a href="{link}" class="cta-btn card-btn">{get_cta_text(link, False)}</a>""" if link else ""

    return f'''
        <div class="card">
          <a href="{detail_link}"><img src="{merch.get('image', '')}" alt="{merch.get('title', '')}" /></a>
          <div class="card-content">
            <h3>{merch.get('title', '')}</h3>
            <p>{artist}</p>
            <p>{merch.get('media', '')}</p>
            <p>{cost}</p>
          </div>
          <div class="card-btn-row">
            <a href="{detail_link}" class="cta-btn card-btn details-btn">Details</a>
            {cta}
          </div>
        </div>
    '''

def render_pot(pot):
    title = pot.get('title', '')
    artist = pot.get('artist', '')
    description = pot.get('description', '')
    year = pot.get('year', '')
    cost = f"""${pot.get('cost')}""" if pot.get('cost') else "Free"
    media = pot.get('media', '')
    image = pot.get('image', '')
    link = pot.get('link')

    slug = slugify(f"{title}-{artist}")
    page_path = Path("shop") / f"{slug}.html"

    # Build pot details section
    details = f"""<div class='event-details'>
    <div class="event-detail">
        <i class="fa-light fa-dollar-sign"></i>
        <div class="event-detail-text">{cost}</div>
    </div>
    """

    details += f"""
    <div class="event-detail">
        <i class="fa-solid fa-mound"></i>
        <div class="event-detail-text">{pot.get('media').replace(',', '<br>')}</div>
    </div>
    """

    details += f"""
    <div class="event-detail">
        <i class="fa-solid fa-dumpster-fire"></i>
        <div class="event-detail-text">{pot.get('firing').replace(',', '<br>')}</div>
    </div>
    """
    if year:
        details += f"""
        <div class="event-detail">
            <i class="fa-regular fa-calendar"></i>
            <div class="event-detail-text">{year}</div>
        </div>
        </div>
        """
    else:
        details += "</div>"


    cta = f"""<a href="{link}" class="cta-btn">{get_cta_text(link, False)}</a>""" if link else ""

    # Load FAQ data for collapsible sections
    faqs = load_json('shop.json').get('faqs')
    
    # Generate collapsible sections
    sections = '\n'.join([
        render_collapsible_detail_section(
            faq.get('title'),
            'fa-solid fa-question',
            faq.get('description', ''),
        )
        for faq in faqs
    ])
 
    # Share section
    sections += render_shop_share_section(title, slug, "pot")

    # Build page content
    page_content = f"""
  <section class="page-details">
    <div class="details-media">
      <img src="{image}" alt="{title}" />
    </div>
    <div class="details-text">
      <h1 class="details-title">{title}</h1>
      <h3>{f"by {artist}" if artist else ""}</h3>
      {details}
      <p class="details-description">{description}</p>
      {cta}
    </div>
  </section>
  
  <section class="event-collapsible-sections">
    {sections}
  </section>
"""

    # Write the page
    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(build_page_html(title, page_content, "shop", "../styles.css"))

def render_merch(merch):
    title = merch.get('title', '')
    artist = merch.get('artist', '')
    media = merch.get('media', '')
    description = merch.get('description', '')
    cost = f"""${merch.get('cost')}""" if merch.get('cost') else "Free"
    image = merch.get('image', '')
    link = merch.get('link')

    slug = slugify(f"{title}-{artist}")
    page_path = Path("shop") / f"{slug}.html"

    # Build merch details section
    details = f"""<div class='event-details'>
    <div class="event-detail">
        <i class="fa-light fa-dollar-sign"></i>
        <div class="event-detail-text">{cost}</div>
    </div>
    """

    details += f"""
    <div class="event-detail">
        <i class="fa-solid fa-hippo"></i>
        <div class="event-detail-text">{media}</div>
    </div>
    </div>
    """

    cta = f"""<a href="{link}" class="cta-btn">{get_cta_text(link, False)}</a>""" if link else ""

    # Load FAQ data for collapsible sections
    faqs = load_json('shop.json').get('faqs')
    
    # Generate collapsible sections
    sections = '\n'.join([
        render_collapsible_detail_section(
            faq.get('title'),
            'fa-solid fa-question',
            faq.get('description', ''),
        )
        for faq in faqs
    ])
 
    # Share section
    sections += render_shop_share_section(title, slug, "item")

    # Build page content - combining media and description with line break
    combined_description = f"{media}<br>{description}" if media and description else (media or description)
    
    page_content = f"""
  <section class="page-details">
    <div class="details-media">
      <img src="{image}" alt="{title}" />
    </div>
    <div class="details-text">
      <h1 class="details-title">{title}</h1>
      <h3>{f"by {artist}" if artist else ""}</h3>
      {details}
      <p class="details-description">{description}</p>
      {cta}
    </div>
  </section>
  
  <section class="event-collapsible-sections">
    {sections}
  </section>
"""

    # Write the page
    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(build_page_html(title, page_content, "shop", "../styles.css"))

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

    # Build event details section
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

    cta = f"""<a href="{link}" class="cta-btn">{get_cta_text(link)}</a>""" if link else ""

    # Load visit data for collapsible sections
    visit = load_json('visit.json')
    
    # Generate collapsible sections
    sections = '\n'.join([
        render_collapsible_detail_section(
            section.get('title'),
            section.get('icon', ''),
            section.get('description', ''),
            section.get('lists', []),
            section.get('image'),
            section.get('iframe'),
            section.get('link'),
            section.get('cta'),
            reverse=(index % 2 != 0)
        )
        for index, section in enumerate(visit.get('sections', [])[1:])
    ])
 
    # Share section
    sections += render_share_section(title, slug)

    # Build page content
    page_content = f"""
  <section class="page-details">
    <div class="details-media">
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
    {sections}
  </section>
"""

    # Write the page
    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(build_page_html(title, page_content, "event", "../styles.css"))

def render_event_card(e):
    cost = f"${e['cost']}" if e.get('cost') else '&nbsp;'
    instructor = f"w/ {e['instructor']}" if e.get('instructor') else '&nbsp;'
    slug = f"{slugify(e['name'])}-{e.get('date')}"
    detail_link = f"event/{slug}.html"

    link = e.get('link')
    cta = f"""<a href="{link}" class="cta-btn card-btn">{get_cta_text(link)}</a>""" if link else ""

    event_data = get_event_card_data(e)

    return f'''
        <div class="card" {event_data}>
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

def render_maker_links(maker):
    instagram = maker.get('instagram')
    website = maker.get('website')

    if instagram and website:
        return f'''
                <a href="{instagram}" target="_blank" class="card-link half">
                    <i class="fa-brands fa-instagram"></i>
                </a>
                <a href="{website}" target="_blank" class="card-link half">
                    <i class="fa-solid fa-link"></i>
                </a>
        '''
    elif instagram:
        return f'''
                <a href="{instagram}" target="_blank" class="card-link full">
                    <i class="fa-brands fa-instagram"></i>
                </a>
        '''
    elif website:
        return f'''
                <a href="{website}" target="_blank" class="card-link full">
                    <i class="fa-solid fa-link"></i>
                </a>
        '''
    return ""

def render_maker(maker, upcoming=''):
    name = maker.get('name', '')
    image = maker.get('image', '')
    statement = maker.get('statement', '')

    slug = slugify(name)
    page_path = Path("maker") / f"{slug}.html"
    links = render_maker_links(maker)

    if upcoming:
      upcoming = f"""
  <section class="page-details homepage-details">
    <div class="details-text">
      <h2>Upcoming Events</h2>
      <div class="carousel">
        {upcoming}
      </div>
    </div>
  </section>
"""

    page_content = f"""
  <section class="page-details">
    <div class="details-media">
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
  {upcoming}
"""

    page_path.parent.mkdir(parents=True, exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(build_page_html(name, page_content, "makers", "../styles.css"))

def render_maker_cards(makers, title="Members"):
    cards = ''
    for m in makers:
        links = render_maker_links(m)
        slug = slugify(m.get("name", ""))
        profile_link = f"maker/{slug}.html"

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
    return f'''<h2 id="{slugify(title)}" class="page-header maker-header">{title}</h2>
<section class="card-grid">
  {cards}
</section>
''' if cards else ""

def render_shop():
    shop = load_json('shop.json')
    pots = shop.get('pots')
    merch = shop.get('merch')

    events = get_events()
    paid_events = [e for e in events if e.get('cost')]

    # Generate individual item pages
    for pot in pots:
        render_pot(pot)
    
    for item in merch:
        render_merch(item)


    shop_nav = f"""
      <div class="page-nav maker-nav"><div class="page-links">
        {''.join(f'<a href="#{slugify(title)}" class="page-link">{title}</a>' for title in ["Pots", "Merch", "Classes & Workshops", "FAQs"])}
        </div>
      </div>"""

    # Generate card sections
    pots_cards = ''.join(render_pot_card(pot) for pot in pots)
    merch_cards = ''.join(render_merch_card(item) for item in merch)
    events_cards = ''.join(render_event_card(e) for e in paid_events)

    # Generate FAQ section with lorem ipsum
    faqs = shop.get('faqs', )
    
    faq_sections = '\n'.join([
        render_collapsible_detail_section(
            faq.get('title'),
            'fa-solid fa-question',
            faq.get('description', ''),
        )
        for faq in faqs
    ])

    # Build shop page content
    content = f'''
  {render_hero("Shop", shop.get('hero'))}
  {shop_nav}
  
  <h2 id="pots" class="page-header">Pots</h2>
  <section class="card-grid">
    {pots_cards}
  </section>
  
  <h2 id="merch" class="page-header">Merch</h2>
  <section class="card-grid">
    {merch_cards}
  </section>
  
  <h2 id="classes-workshops" class="page-header">Classes & Workshops</h2>
  <section class="card-grid">
    {events_cards}
  </section>
  
  <h2 id="faqs" class="page-header">FAQs</h2>
  <section class="event-collapsible-sections">
    {faq_sections}
  </section>
'''

    with open('shop.html', 'w', encoding='utf-8') as f:
        f.write(build_page_html("Shop", content, "shop"))

def render_home():
    home = load_json('home.json')
    testimonials = home.get('testimonials', [])
    events = get_events()
    upcoming = events[:3]

    title_with_br = home.get('title', '').replace(NEWLINE, '<br>')

    upcoming_cards = ''.join(render_event_card(e) for e in upcoming)

    testimonial_cards = ''.join(f'''
    <div class="testimonial-card">
      <img src="{t.get('image', '')}" alt="Testimonial Background">
      <div class="testimonial-text">
        <h2>"{t.get('text', '')}"</h2>
        <p>- {t.get('name', '')}, {t.get('location', '')}</p>
      </div>
    </div>
    ''' for t in testimonials[:10])

    email_octopus = home.get('email_octopus')
    email_octopus_btn = f'''<a class="cta-btn" data-eo-form-toggle-id="{email_octopus.get('id')}" href="#">{email_octopus.get('cta')}</a>''' if email_octopus.get('id') else ''
    email_octopus_script = f'''<script async src="https://eocampaign1.com/form/{email_octopus.get('id')}.js" data-form="{email_octopus.get('id')}"></script>''' if email_octopus.get('id') else ''

    content = f'''
  {render_hero(title_with_br, home.get('hero'))}
  <section class="page-details homepage-details">
    <div class="details-text">
      <p class="details-description home">{home.get('description')}</p>
      {email_octopus_btn}
    </div>
  </section>
  <section class="page-details homepage-details">
    <div class="details-text">
      <h2>Upcoming Events</h2>
      <div class="carousel">
        {upcoming_cards}
      </div>
      <a href="schedule.html" class="cta-btn">Full Schedule of Events</a>
    </div>
  </section>
  <section class="page-details homepage-details">
    <div class="details-text">
      <div class="carousel">
        {testimonial_cards}
      </div>
    </div>
  </section>
{email_octopus_script}
'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(build_page_html("Chicago Clay Co-Op", content, "home"))

def render_about():
    about = load_json('about.json')

    sections = '\n'.join([
        render_detail_section(
            section.get('title'),
            section.get('icon'),
            section.get('description', ''),
            section.get('lists', []),
            section.get('image'),
            section.get('iframe'),
            section.get('link'),
            section.get('cta'),
            reverse=(index % 2 != 0)
        )
        for index, section in enumerate(about.get('sections', []))
    ])

    content = f'''
  {render_hero("About", about.get('hero'))}
  {sections}
'''

    with open('about.html', 'w', encoding='utf-8') as f:
        f.write(build_page_html("About", content, "about"))

def render_visit():
    visit = load_json('visit.json')

    sections = '\n'.join([
        render_detail_section(
            section.get('title'),
            section.get('icon'),
            section.get('description', ''),
            section.get('lists', []),
            section.get('image'),
            section.get('iframe'),
            section.get('link'),
            section.get('cta'),
            reverse=(index % 2 != 0)
        )
        for index, section in enumerate(visit.get('sections', []))
    ])

    content = f'''
  {render_hero("Visit", visit.get('hero'))}
  {sections}
'''

    with open('visit.html', 'w', encoding='utf-8') as f:
        f.write(build_page_html("Visit", content, "visit"))

def render_schedule():
    json_events = load_json('events.json')

    # Group events by month
    grouped = {}
    for e in get_events():
        render_event(e)

        if 'date' not in e:
            continue
        dt = datetime.strptime(e['date'], "%Y-%m-%d")
        month_label = dt.strftime('%B')
        grouped.setdefault(month_label, []).append(e)

    month_nav = ''.join(f'<a href="#{month.lower()}" class="page-link">{datetime.strptime(month, "%B").strftime("%b")}</a>\n' for month in grouped.keys())

    # Build the content
    content_blocks = ''.join(f'''
        <h2 id="{month.lower()}" class="page-header">{month}</h2>
        <section class="card-grid">
          {''.join(render_event_card(e) for e in events_in_month)}
        </section>
        ''' for month, events_in_month in grouped.items())

    content = f'''
  {render_hero("Schedule of Events", json_events.get('hero'))}
  <div class="page-nav">
    <details class="filter-section">
      <summary class="filter-toggle">
        <i class="fa-solid fa-sliders"></i>
        <p>Filter</p>
      </summary>
      <div class="filter-content">
        <div class="filter-group">
          <h4>Time of Day</h4>
          <label><input type="checkbox" name="morning"> Morning</label>
          <label><input type="checkbox" name="afternoon"> Afternoon</label>
          <label><input type="checkbox" name="evening"> Evening</label>
        </div>
        
        <div class="filter-group">
          <h4>Type</h4>
          <label><input type="checkbox" name="workshop"> Workshop</label>
          <label><input type="checkbox" name="class"> Class</label>
          <label><input type="checkbox" name="free"> Free</label>
        </div>
        
        <div class="filter-group">
          <h4>Time of Week</h4>
          <label><input type="checkbox" name="weekday"> Weekday</label>
          <label><input type="checkbox" name="weekend"> Weekend</label>
        </div>
        
        <div class="filter-group">
          <h4>Technique</h4>
          <label><input type="checkbox" name="handbuilding"> Handbuilding</label>
          <label><input type="checkbox" name="wheelthrowing"> Wheelthrowing</label>
        </div>
      </div>
    </details>
    <div class="page-links">
      {month_nav}
    </div>
  </div>
  {content_blocks}
'''

    with open('schedule.html', 'w', encoding='utf-8') as f:
        f.write(build_page_html("Schedule", content, "schedule"))

def render_makers():
    makers = load_json('makers.json')
    members = makers.get('members', [])
    visitors = makers.get('visitors', [])

    events = load_json('events.json')

    for maker in members + visitors:
        render_maker(maker, ''.join([render_event_card(e) for e in events.get('events') if e.get('instructor','') == maker.get('name')]))

    members_section = render_maker_cards(members)
    visitors_section = render_maker_cards(visitors, 'Visiting Artists')

    maker_nav = ''
    if members_section and visitors_section:
      maker_nav = f'<div class="page-nav maker-nav"><div class="page-links">'
      maker_nav += ''.join(f'<a href="#{slugify(title)}" class="page-link">{title}</a>\n' for title in ["Members", "Visiting Artists"])
      maker_nav +=  f'</div></div>'

    content = f'''
  {render_hero("Makers", makers.get('hero'))}
  {maker_nav}
  <section class="page-details homepage-details">
    <div class="details-text">
      <p class="details-description home">{makers.get('description')}</p>
      <a href="{makers.get('link')}" class="cta-btn">{makers.get('cta')}</a>
    </div>
  </section>
  {members_section}
  {visitors_section}
'''

    with open('makers.html', 'w', encoding='utf-8') as f:
        f.write(build_page_html("Makers", content, "makers"))

def main():
    render_home()
    render_about()
    render_visit()
    render_schedule()
    render_makers()
    render_shop()

if __name__ == '__main__':
    main()
