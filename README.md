# Static Site Generator for Chicago Clay Co-operative

This project generates a static HTML website from JSON data for workshops and members.

## Features

* Member profiles with links to Instagram, websites, shops
* Workshop listings with booking buttons
* Monthly calendar with highlighted workshop dates
* Responsive layout and minimal styling using Flexbox

## How to Use

### 1. Install Python (if not already installed)

You need Python 3.7+.
On macOS you can use Homebrew (optional):

```sh
brew install python3
```

### 2. Clone or download this repository

```sh
git clone git@github.com:mangimangi/chicago-clay-coop.git
```

### 3. Run the generator

Make sure you have your data files: `members.json` and `workshops.json`.

```sh
python generate_site.py members.json workshops.json
```

This will generate:

* `index.html`
* `about.html`
* `members.html`
* `workshops.html`

### 4. Open the files in a browser

Open index.html in your browser to view the local HTML you've generated. If you commit changes to `generate_site.py` or the JSON data they will automatically be deployed to DigitalOcean App Platform.

## Styling

All layout and color styling is defined in `styles.css`, using no inline styles. Fonts are loaded from Google Fonts, and Font Awesome is used for icons.

## Project Structure

```
.
├── generate_site.py       # Main generator script
├── styles.css             # Global stylesheet
├── members.json           # Member data
├── workshops.json         # Workshop data
├── index.html             # Home page (generated)
├── about.html             # About page (generated)
├── members.html           # Members page (generated)
└── workshops.html         # Workshops page (generated)
```

