# NewTab

A modern, customizable homepage manager with flip-card navigation and dynamic page management.

![NewTab Screenshot](https://img.shields.io/badge/Flask-Python-blue) ![Docker](https://img.shields.io/badge/Docker-Ready-green)

## Features

- 🎴 **Flip Cards** - Beautiful flip-card interface for quick navigation
- 📑 **Dynamic Pages** - Create custom pages and assign cards to multiple pages
- 🔍 **Configurable Search** - Enable/disable search bar with custom search URL
- 🎨 **Customizable Cards** - Set custom images, colors, and multiple links per card
- 📱 **Responsive Layout** - Automatically balances card grid for optimal display
- ⚡ **Pagination** - Smart pagination for cards with many links

## Quick Start

### Using Docker Compose

```bash
docker-compose up -d
```

The app will be available at `http://localhost:5000`

### Using Docker Hub

```bash
docker pull devopsteamsdb/devopsteamsdb:newtab_latest
docker run -p 5000:5000 -v ./data.json:/app/data.json -v ./static/img:/app/static/img devopsteamsdb/devopsteamsdb:newtab_latest
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment (development/production) | development |

### Data Persistence

Mount these volumes to persist data:
- `./data.json:/app/data.json` - Cards, pages, and settings
- `./static/img:/app/static/img` - Uploaded card images

## Admin Panel

Access the admin panel at `/admin` to:
- Add/Edit/Delete cards
- Manage pages
- Configure search bar settings

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

## CI/CD

GitHub Actions workflow automatically:
- Builds Docker image on push to main
- Pushes to Docker Hub with date and `latest` tags
- Creates GitHub release with Docker image artifact

### Required Secrets

- `DOCKERHUB_USERNAME` - Docker Hub username
- `DOCKERHUB_PASSWORD` - Docker Hub password/token

## License

MIT License
