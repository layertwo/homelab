# Media Management Stack

This document provides detailed information about the media management stack in the homelab.

## Overview

The media management stack is a collection of applications that work together to automate the downloading, organizing, and streaming of media content. The stack includes:

- **Sonarr**: TV show management
- **Radarr**: Movie management
- **Bazarr**: Subtitle management
- **Prowlarr**: Indexer management
- **qBittorrent**: Download client
- **Jellyfin**: Media server
- **Recyclarr**: Configuration management for *arr apps

## Architecture

The media stack follows the following workflow:

1. **Prowlarr** manages indexers and connects to Sonarr and Radarr
2. **Sonarr** and **Radarr** search for content using Prowlarr and send download requests to qBittorrent
3. **qBittorrent** downloads the content and places it in the appropriate directory
4. **Sonarr** and **Radarr** organize the downloaded content
5. **Bazarr** downloads subtitles for the content
6. **Jellyfin** scans the organized content and makes it available for streaming
7. **Recyclarr** keeps the *arr apps configured with best practices

## Components

### Sonarr

Sonarr is an application that manages TV shows. It can automatically search for and download new episodes as they become available.

#### Configuration

- **URL**: sonarr.layertwo.dev
- **Storage**: PVC for configuration and database
- **Media Path**: /media/tv

### Radarr

Radarr is an application that manages movies. It can automatically search for and download movies based on a watchlist.

#### Configuration

- **URL**: radarr.layertwo.dev
- **Storage**: PVC for configuration and database
- **Media Path**: /media/movies

### Bazarr

Bazarr is an application that manages subtitles. It can automatically search for and download subtitles for TV shows and movies.

#### Configuration

- **URL**: bazarr.layertwo.dev
- **Storage**: PVC for configuration and database
- **Media Paths**:
  - /media/tv
  - /media/movies

### Prowlarr

Prowlarr is an application that manages indexers. It provides a unified interface for searching across multiple indexers and can sync indexers with Sonarr and Radarr.

#### Configuration

- **URL**: prowlarr.layertwo.dev
- **Storage**: PVC for configuration and database

### qBittorrent

qBittorrent is a download client that handles the actual downloading of content.

#### Configuration

- **URL**: qbittorrent.layertwo.dev
- **Storage**: PVC for configuration and downloads
- **Download Path**: /downloads

### Jellyfin

Jellyfin is a media server that provides a web interface for browsing and streaming media content.

#### Configuration

- **URL**: jellyfin.layertwo.dev
- **Storage**: PVC for configuration and metadata
- **Media Paths**:
  - /media/tv
  - /media/movies

### Recyclarr

Recyclarr is a tool that synchronizes recommended settings from the TRaSH guides to Sonarr and Radarr.

#### Configuration

- Runs as a CronJob
- Configures quality profiles, custom formats, and release profiles

## Storage

The media stack uses persistent storage for both configuration and media content:

- **Configuration**: Each application has its own PVC for storing configuration and databases
- **Media**: Shared storage is used for media content, with separate directories for TV shows and movies

## Networking

The media stack is exposed through the internal Traefik instance:

- Each application has its own subdomain (e.g., sonarr.layertwo.dev)
- Authentication is handled by Authentik

## Maintenance

### Updating

The applications are updated automatically through Flux CD when new versions are available in the Helm repositories.

### Backup

- Configuration is backed up using VolSync
- Media content should be backed up separately if needed

## Troubleshooting

### Download Issues

If downloads are not working:

1. Check that qBittorrent is running and accessible
2. Verify that Sonarr and Radarr can connect to qBittorrent
3. Check that Prowlarr is configured correctly and can connect to indexers

### Streaming Issues

If streaming is not working:

1. Check that Jellyfin is running and accessible
2. Verify that Jellyfin can access the media directories
3. Check that the media files are in a format that Jellyfin can play

### Subtitle Issues

If subtitles are not being downloaded:

1. Check that Bazarr is running and accessible
2. Verify that Bazarr can connect to Sonarr and Radarr
3. Check that Bazarr is configured with subtitle providers
