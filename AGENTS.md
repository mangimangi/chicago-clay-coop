# Agent Instructions for Chicago Clay Coop

This project uses **beads** (bd CLI) for issue tracking and coordination across multiple AI agents and human studio members working on this project.

## Project Overview

**Chicago Clay Coop** is transitioning from a static Python site generator to a modern web API + Discord bot architecture with Stripe integration.

### Current Architecture (Baseline)
- **Frontend**: Static HTML generated from JSON by `generate_site.py`
- **Data**: JSON files in `/json/` directory
- **Hosting**: Digital Ocean App Platform (free static tier)
- **CI/CD**: GitHub Actions JSON validation

### Target Architecture
- **Frontend**: Same static HTML generation, hosted on DO App Platform (free)
- **Backend API**: FastAPI server on DO App Platform ($5/month)
- **Data Storage**: Digital Ocean Spaces bucket (`file-the-coop`)
- **Discord Bot**: Integration for member/event/workshop/class updates
- **Email**: Email Octopus integration for newsletters and reminders
- **Payments**: Stripe integration (checkout + inventory management)
- **Rebuild Trigger**: GitHub Actions watches Spaces for JSON changes → triggers site rebuild

## Quick Reference

```bash
bd ready              # Find available work (sorted by priority)
bd show <id>          # View issue details and subtasks
bd update <id> --status in_progress  # Claim work
bd close <id>         # Mark work complete
bd sync               # Sync issues to git
```

## Understanding This Project's Development Flow

### Key Files & Components

**Python Generator & JSON Data**
- `generate_site.py` (1,061 lines) - Main static site generator
- `/json/` - Data files: `home.json`, `makers.json`, `events.json`, `shop.json`, `about.json`, `visit.json`
- `styles.css` - Responsive styling (994 lines)

**New Components Being Built**
- `api/` - FastAPI application (TBD)
- Discord bot integration (TBD)
- Email Octopus service layer (TBD)
- Stripe integration (TBD)

## JSON Data Schemas

The site generator reads data from JSON files in the `/json/` directory. Below are the schemas for each file.

### home.json

Main site configuration and homepage content.

```json
{
  "thumbnail": "string (URL)",       // Site favicon/thumbnail image
  "hero": "string (URL)",            // Homepage hero image
  "title": "string",                 // Homepage title (supports \\n for line breaks)
  "description": "string",           // Site description
  "email_octopus": {
    "id": "string",                  // Email Octopus form ID
    "cta": "string"                  // Button text for newsletter signup
  },
  "email": "string",                 // Contact email
  "phone": "string",                 // Contact phone
  "instagram": "string (URL)",       // Instagram profile URL
  "apply": "string (URL)",           // Membership application URL
  "testimonials": [                  // Array of testimonials
    {
      "name": "string",              // Testimonial author name
      "location": "string",          // Author location
      "text": "string",              // Testimonial quote
      "image": "string (URL)"        // Background image for testimonial card
    }
  ]
}
```

### events.json

Events, workshops, and classes schedule.

```json
{
  "hero": "string (URL)",            // Events page hero image
  "events": [                        // Array of events
    {
      "name": "string",              // Event title (required)
      "date": "string (YYYY-MM-DD)", // Single event date (required if no dates)
      "dates": ["string"],           // Array of dates for multi-session classes (optional)
      "time": "string",              // Event time (e.g., "6pm-9pm")
      "cost": "string|number",       // Price (omit for free events)
      "instructor": "string",        // Instructor name (optional)
      "description": "string",       // Event description
      "image": "string (URL)",       // Event image
      "link": "string (URL)",        // Registration/purchase link (optional)
      "technique": "string",         // Technique type: "handbuilding", "wheelthrowing" (optional)
      "requirements": "string",      // Requirements (e.g., "Ages 21+") (optional, defaults to "Open to All")
      "callout": "string"            // Callout badge text (e.g., "NEW") (optional)
    }
  ]
}
```

**Notes:**
- Use `date` for single events, `dates` array for multi-session classes
- If `dates` is provided, the minimum date is used for sorting
- Events with `cost` and `dates` are categorized as "class"
- Events with `cost` but no `dates` are categorized as "workshop"
- Events without `cost` are categorized as "free"

### makers.json

Studio members and visiting artists.

```json
{
  "hero": "string (URL)",            // Makers page hero image
  "description": "string",           // Page description
  "cta": "string",                   // Call-to-action button text
  "link": "string (URL)",            // CTA link (e.g., membership inquiry)
  "members": [                       // Array of studio members
    {
      "name": "string",              // Artist name (required)
      "statement": "string",         // Artist statement/bio
      "image": "string (URL)",       // Artist photo
      "instagram": "string (URL)",   // Instagram profile URL (optional)
      "website": "string (URL)",     // Personal website URL (optional)
      "shop": "string (URL)"         // Online shop URL (optional)
    }
  ],
  "visitors": [                      // Array of visiting artists (same schema as members)
    { ... }
  ]
}
```

### shop.json

Products for sale and FAQs.

```json
{
  "hero": "string (URL)",            // Shop page hero image
  "pots": [                          // Array of ceramic pieces for sale
    {
      "title": "string",             // Item title (required)
      "artist": "string",            // Artist name
      "media": "string",             // Materials (e.g., "Stoneware, Porcelain")
      "firing": "string",            // Firing method (e.g., "Cone 10, Reduction")
      "year": "string|number",       // Year created
      "cost": "number",              // Price in dollars (required for API checkout)
      "description": "string",       // Item description
      "image": "string (URL)",       // Item image
      "link": "string (URL)"         // Legacy: direct Stripe link (optional, see Payment section)
    }
  ],
  "merch": [                         // Array of merchandise items
    {
      "title": "string",             // Item title (required)
      "artist": "string",            // Creator/brand name
      "media": "string",             // Material (e.g., "Vinyl", "Cotton")
      "cost": "number",              // Price in dollars (required for API checkout)
      "description": "string",       // Item description
      "image": "string (URL)",       // Item image
      "link": "string (URL)"         // Legacy: direct Stripe link (optional, see Payment section)
    }
  ],
  "faqs": [                          // Array of frequently asked questions
    {
      "title": "string",             // Question
      "description": "string"        // Answer
    }
  ]
}
```

**Note:** The `link` field is optional. Products can use either:
1. **API Checkout** (preferred): Omit `link`, use `POST /api/stripe/checkout/product/{slug}` endpoint
2. **Direct Link** (legacy): Include a pre-created Stripe payment link in `link` field

### about.json

About page sections.

```json
{
  "hero": "string (URL)",            // About page hero image
  "sections": [                      // Array of content sections
    {
      "title": "string",             // Section title (supports \\n for line breaks)
      "icon": "string",              // FontAwesome icon class (optional)
      "description": "string",       // Section content (supports \\n for line breaks)
      "image": "string (URL)",       // Section image (optional)
      "iframe": "string (URL)",      // Embedded iframe URL (optional, e.g., Google Maps)
      "cta": "string",               // Button text (optional)
      "link": "string (URL)",        // Button link (optional)
      "lists": [                     // Array of bulleted lists (optional)
        {
          "title": "string",         // List heading
          "icon": "string",          // FontAwesome icon class
          "items": ["string"]        // Array of list items
        }
      ]
    }
  ]
}
```

### visit.json

Visit page with location and logistics info.

```json
{
  "hero": "string (URL)",            // Visit page hero image
  "sections": [                      // Array of content sections (same schema as about.json)
    {
      "title": "string",             // Section title (supports \\n for addresses)
      "icon": "string",              // FontAwesome icon class (optional)
      "description": "string",       // Section content
      "image": "string (URL)",       // Section image (optional)
      "iframe": "string (URL)",      // Embedded iframe (e.g., Google Maps embed)
      "cta": "string",               // Button text (optional)
      "link": "string (URL)",        // Button link (optional)
      "lists": [                     // Array of bulleted lists
        {
          "title": "string",         // List heading
          "icon": "string",          // FontAwesome icon class
          "items": ["string"]        // Array of list items
        }
      ]
    }
  ]
}
```

### Common Patterns

**URLs:**
- Image URLs typically use Imgur hosting (e.g., `https://i.imgur.com/xxx.jpeg`)
- Internal links use relative paths (e.g., `/events.html`)

**Line Breaks:**
- Use `\\n` in JSON strings for line breaks (rendered as `<br>` in HTML)

**Icons:**
- Uses FontAwesome 6.5+ classes (e.g., `fa-solid fa-phone`, `fa-brands fa-instagram`)
- See [FontAwesome Icons](https://fontawesome.com/icons) for reference

**Date Format:**
- All dates use ISO 8601 format: `YYYY-MM-DD`

**Payment Integration:**

Two approaches are supported:

1. **API Checkout Sessions** (preferred for shop items):
   - Frontend calls `POST /api/stripe/checkout/product/{slug}` with product slug
   - API looks up product in shop.json, creates Stripe Checkout session
   - Returns checkout URL for redirect
   - No pre-created payment links needed in JSON

2. **Direct Stripe Links** (legacy, still works for events):
   - Include `link` field with Stripe payment link (e.g., `https://buy.stripe.com/xxx`)
   - Static site generator renders link directly
   - Useful for events with custom registration flows

**CTA Button Text:**
- Stripe links (`*.stripe.com`) → "Register" (events) or "Buy" (shop)
- Non-Stripe links → "Learn More"

### API Endpoints

The FastAPI backend provides these endpoints:

**Stripe Checkout:**
- `POST /api/stripe/checkout` - Create checkout session with custom product
- `POST /api/stripe/checkout/product/{slug}` - Create checkout for shop.json product by slug
- `POST /api/stripe/webhook` - Handle Stripe webhook events

**Site Rebuild:**
- `POST /api/rebuild/trigger` - Trigger GitHub Actions site rebuild

**Health:**
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check (dependencies)
- `GET /health/live` - Liveness check

### Development Phases (from Beads)

**Phase 0: Testing & Documentation** - Baseline validation
- Test existing `generate_site.py` pipeline (verify all HTML generation works)
- Document JSON schema/structure for all data files (reference for bot/API developers)

**Phase 1: Local Development & Infrastructure** - FastAPI setup and Spaces integration
- Create FastAPI project structure with dependencies
- Set up DO Spaces client utilities for JSON management

**Phase 2: Email Management** - Email Octopus integration
- Listserv management, event/workshop/class reminders

**Phase 3: Discord Bot - Priority Features** - Member/event/workshop/class updates (more important than shop)
- Bot setup and slash command infrastructure (runs in FastAPI as background task)
- Member management commands (/member add, update, remove, list)
- Event/workshop/class commands (/event, /workshop, /class commands)

**Phase 4: Stripe Integration** - Shop product management and checkout
- Stripe API client and product catalog sync
- Checkout session endpoint
- Webhook receiver for payment confirmation and inventory sync

**Phase 5: Site Rebuild Automation** - CI/CD and automatic updates
- GitHub Actions workflow to monitor Spaces for JSON changes
- API webhook to trigger GitHub Actions rebuilds

**Phase 6: Frontend Integration** - Stripe Checkout on website
- Integrate Stripe Checkout button into shop page
- Handle success/cancel redirects

**Phase 7: Deployment & Testing** - Production deployment
- Package FastAPI for DO App Platform
- End-to-end integration testing

### JSON Data Flow

When someone updates data via Discord or API:
1. **Discord/API** → Updates JSON in Digital Ocean Spaces
2. **Spaces webhook** → Triggers GitHub Actions workflow
3. **GitHub Actions** → Pulls repo, runs `python3 generate_site.py`, deploys HTML to DO App Platform
4. **Stripe sync** (optional) - Discord command may also sync to Stripe inventory

### Discord Bot Architecture

The Discord bot runs **in the same FastAPI process** as a background task (using asyncio). This keeps deployment simple and costs low ($5/month for the entire backend):

**How it works:**
1. **FastAPI application starts** with Discord bot as a background task
2. **Discord bot connects** to Discord's WebSocket gateway using discord.py
3. **Studio member types slash command** in Discord (e.g., `/member add "Jane" "Makes sculptures"`)
4. **Discord sends interaction** to the bot (via WebSocket)
5. **Bot processes command** → calls internal API functions
6. **Functions update JSON** in Digital Ocean Spaces
7. **Spaces triggers GitHub Actions** → website rebuilds
8. **Discord bot sends response** to studio member with confirmation/errors

**Architecture diagram:**
```
┌─────────────────────────────────────────┐
│   Digital Ocean App Platform ($5)       │
├─────────────────────────────────────────┤
│  FastAPI Application                    │
│  ├─ /api/* endpoints (Stripe, etc)     │
│  ├─ Discord bot (background task)      │
│  │  └─ Runs discord.py client          │
│  │  └─ Listens for slash commands      │
│  ├─ Services                            │
│  │  ├─ Spaces client                   │
│  │  ├─ Email Octopus client            │
│  │  ├─ Stripe client                   │
│  │  └─ GitHub Actions trigger          │
│  └─ Session management & auth          │
└──────────────────────────────────────────┘
         ↓                    ↑
   Updates JSON         Sends responses
         ↓                    ↑
┌──────────────────┐   ┌─────────────────┐
│ DO Spaces JSON   │   │  Discord API    │
│ (file-the-coop)  │   │  (WebSocket)    │
└──────────────────┘   └─────────────────┘
         ↓
┌──────────────────┐
│ GitHub Actions   │ → Rebuild & Deploy HTML
│  Rebuild Trigger │
└──────────────────┘
```

**Key benefits:**
- Single deployment = lower cost and complexity
- Shared state/services (Spaces client, configs, etc)
- Same HTTP endpoints for both API and discord.py webhook interactions
- Easier to test (single process locally)

### Development Guidelines

**Before Starting Work**
- Run `bd show <issue-id>` to understand requirements
- Check related issues in the description
- Review any subtasks

**During Development**
- Keep commits focused and descriptive
- Test locally before pushing
- Update issue status with `bd update <id> --status in_progress` when starting
- No external dependencies: this project uses only Python 3.7+ stdlib

**Before Ending Session**
- Close completed issues: `bd close <id>`
- Create new issues for discovered work: `bd create "Description"`
- See "Landing the Plane" section below

## Technology Stack

| Component | Tech | Notes |
|-----------|------|-------|
| Static Site | Python 3.7+ | No external deps, stdlib only |
| API | FastAPI | Python async framework |
| Bot | discord.py | Discord interactions API |
| Email | Email Octopus API | Newsletter & reminders |
| Payments | Stripe API | Checkout sessions + inventory |
| Data Storage | Digital Ocean Spaces (S3) | JSON files + media |
| Hosting (API) | DO App Platform | $5/month |
| Hosting (Static) | DO App Platform | Free tier |
| CI/CD | GitHub Actions | JSON validation + rebuild triggers |

## Environment Variables & Secrets

When setting up the FastAPI server, you'll need:
- `DIGITALOCEAN_SPACES_ACCESS_KEY` - DO Spaces bucket access
- `DIGITALOCEAN_SPACES_SECRET_KEY` - DO Spaces bucket secret
- `DIGITALOCEAN_REGION` - DO Spaces region
- `DISCORD_BOT_TOKEN` - Discord bot authentication
- `DISCORD_WEBHOOK_URL` - For async event notifications (optional)
- `STRIPE_API_KEY` - Stripe account API key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret
- `EMAIL_OCTOPUS_API_KEY` - Email Octopus list management
- `GITHUB_TOKEN` - For triggering Actions workflows (optional)

Store these in DO App Platform environment settings and DO Spaces lifecycle rules, NOT in git.

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create new issues for any discovered gaps:
   ```bash
   bd create "Your task description"
   ```

2. **Run quality gates** (if code changed):
   ```bash
   # For Python code
   python3 -m pytest  # If tests exist
   python3 -m pylint <files>  # If using linter
   ```

3. **Update issue status** - Close finished work:
   ```bash
   bd close <issue-id>  # or bd update <id> --status completed
   ```

4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push origin claude/setup-beads-integration-YOFBq
   git status  # MUST show "Your branch is up to date with 'origin/claude/setup-beads-integration-YOFBq'"
   ```

5. **Clean up**:
   ```bash
   git stash clear
   git remote prune origin
   ```

6. **Verify** - All changes committed AND pushed:
   ```bash
   git log --oneline -5  # See your commits
   git status  # Should show no changes
   ```

7. **Hand off** - Provide context:
   - Summary of completed work
   - Any blockers or decisions made
   - Suggested next issues to tackle

**CRITICAL RULES:**
- ✋ **STOP** - Work is NOT complete until `git push` succeeds
- ✋ **NEVER** stop before pushing - that leaves work stranded locally
- ✋ **NEVER** say "ready to push when you are" - YOU must push immediately
- ✋ **NEVER** skip `git status` verification
- ✋ If push fails, resolve and retry until it succeeds
- ✋ NEVER ignore merge conflicts - resolve them

## Useful Beads Commands

```bash
# Finding work
bd ready                           # Issues ready to start
bd ready --label <label>           # Filter by label
bd show <id>                       # View issue details

# Managing work
bd create "Description"            # Create new issue
bd update <id> --status in_progress   # Claim issue
bd update <id> --description "..."    # Update description
bd close <id>                      # Complete issue

# Viewing history
bd log                             # Recent activity
bd log <id>                        # Activity for one issue
bd show <id> --details             # Full issue details

# Syncing & configuration
bd sync                            # Commit issues to git
bd config get/set <key> <value>    # Manage configuration
```

## Common Workflows

### Starting New Work
```bash
bd ready                           # See what needs doing
bd show chicago-clay-coop-xxx      # Review issue
bd update chicago-clay-coop-xxx --status in_progress  # Claim it
# ... do work ...
bd close chicago-clay-coop-xxx     # Mark complete
```

### Creating Subtasks
```bash
# Create main issue
bd create "Implement Stripe checkout flow"

# Within that issue (add to description):
# - [ ] Create Stripe API client
# - [ ] Implement checkout session endpoint
# - [ ] Add Stripe webhook handler
```

### Discovering New Work During Development
```bash
# Found a bug or new requirement?
bd create "Bug: Payment link detection fails on mobile"
bd create "Feature: Add inventory sync to Stripe"
# Continue with current work, hand off new issues to next session
```

## Coordination Between Agents & Humans

This project will have multiple actors:
- **Claude agents** - Working via beads on features/fixes
- **Studio members** - Updating data via Discord bot (they won't use beads)
- **API** - Syncing data between Discord → Spaces → Stripe → HTML

When implementing Discord commands or Email Octopus features:
- Consider the user experience (studio members aren't developers)
- Test with realistic data before deploying
- Document commands in issue descriptions for reference

## Testing & Validation

**Before pushing code for:**

**Discord Bot Features**
- Test slash commands work in a test Discord server
- Verify JSON updates are valid
- Check Spaces sync completes

**API Endpoints**
- Test with curl or Postman
- Verify request validation
- Check error handling

**Stripe Integration**
- Use Stripe's test mode
- Verify webhook payloads
- Test checkout flow end-to-end

**Email Octopus**
- Use Email Octopus sandbox mode
- Test listserv management
- Verify reminder templates

## Getting Help

- Run `bd show <issue-id>` for issue context
- Check issue descriptions for requirements and dependencies
- Ask clarifying questions in issue comments (via `bd update`)
- Review code from related issues

