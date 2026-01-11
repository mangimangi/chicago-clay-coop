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

