# Media Management Stack

This document provides detailed information about the media management stack in the homelab.

## Overview

The media management stack is a collection of applications that work together to automate the downloading, organizing, and streaming of media content. The stack includes:

- **Sonarr**: TV show management
- **Radarr**: Movie management
- **Bazarr**: Subtitle management
- **Prowlarr**: Indexer management
- **qBittorrent**: Download client (routed through a Gluetun VPN sidecar)
- **Jellyfin**: Media server
- **Recyclarr**: Configuration management for *arr apps
- **FlareSolverr**: Helps Prowlarr solve Cloudflare/anti-bot challenges on indexers

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
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster
- **Media Paths**:
  - /shows
  - /downloads

### Radarr

Radarr is an application that manages movies. It can automatically search for and download movies based on a watchlist.

#### Configuration

- **URL**: radarr.layertwo.dev
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster
- **Media Paths**:
  - /movies
  - /downloads

### Bazarr

Bazarr is an application that manages subtitles. It can automatically search for and download subtitles for TV shows and movies.

#### Configuration

- **URL**: bazarr.layertwo.dev
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster
- **Media Paths**:
  - /movies
  - /tv

### Prowlarr

Prowlarr is an application that manages indexers. It provides a unified interface for searching across multiple indexers and can sync indexers with Sonarr and Radarr.

#### Configuration

- **URL**: prowlarr.layertwo.dev
- **Storage**: PVC for configuration; database is a dedicated CloudNativePG (CNPG) PostgreSQL cluster

### FlareSolverr

FlareSolverr is a proxy server that solves Cloudflare and other anti-bot challenges. It is deployed alongside the rest of the stack and used by Prowlarr to work around indexers protected by these challenges.

### qBittorrent

qBittorrent is a download client that handles the actual downloading of content. All torrent traffic is routed through a **Gluetun** VPN sidecar container, paired with a **port-forward manager** sidecar that keeps qBittorrent's listening port in sync with the VPN provider's dynamically assigned forwarded port.

#### Configuration

- **URL**: qt.layertwo.dev
- **Storage**: PVC for configuration and downloads
- **Download Path**: /data/downloads

### Jellyfin

Jellyfin is a media server that provides a web interface for browsing and streaming media content.

#### Configuration

- **URL**: jellyfin.layertwo.dev
- **Storage**: PVC for configuration and metadata
- **Media Paths**:
  - /movies
  - /tv

#### Hardware transcoding

Jellyfin transcodes on the **RTX 2080** in `node-nv1` (Turing TU104, 8 GB), moved there from
the Intel iGPU on 2026-08-23. The Kaby Lake iGPU on node1-3 handles 4K HEVC 8-bit decode
poorly and 4K HDR tone-mapping worse.

The pod is placed by `nodeSelector: feature.node.kubernetes.io/pci-0300_10de.present: "true"`
and reaches the card via `runtimeClassName: nvidia`.

##### Why there is no NVIDIA device plugin or GPU Operator

Deliberate. Everything they would install is already present on `node-nv1`:

| Component | Provided by |
|---|---|
| NVIDIA driver | Host package (595.84) |
| `nvidia-container-toolkit` | Host package |
| containerd `nvidia` runtime | k3s auto-detected the toolkit and wrote it into its containerd config |
| `nvidia` RuntimeClass | Created by k3s |
| GPU node label | NFD's built-in PCI source — `feature.node.kubernetes.io/pci-0300_10de.present` |

That leaves the **device plugin**, whose only job is to advertise `nvidia.com/gpu` so the
scheduler can count GPUs. With one GPU on one node and every manifest under our control,
that accounting buys nothing — pods reach the card directly through the runtime class:

```yaml
pod:
  runtimeClassName: nvidia
env:
  NVIDIA_VISIBLE_DEVICES: all
  NVIDIA_DRIVER_CAPABILITIES: all
```

The **GPU Operator** is a wrapper that installs the driver, toolkit, and device plugin across
fleets of heterogeneous nodes. Here it would reinstall what the OS already provides (its
driver containers can actively conflict with a host-installed driver) to deliver a plugin we
don't want. Its one genuinely useful extra, the DCGM metrics exporter, has nowhere to send
metrics — the cluster runs Gatus for health checks, with no Prometheus.

Sharing modes were evaluated and rejected:

- **MPS** multiplexes *CUDA contexts between processes*. There is only one long-lived CUDA
  process here, so there is no CUDA-vs-CUDA contention to mediate. It also divides VRAM
  strictly evenly — `perDevicePinnedDeviceMemoryLimits` computes `totalMemory/replicas` and
  applies it as a daemon-wide default, with no per-client override — so 8 GB can only ever be
  split 4/4 or 2/2/2/2, never the asymmetric split these workloads want.
- **Time-slicing** only makes the plugin advertise N allocatable units so a second pod isn't
  left `Pending`. It provides no isolation of any kind. Since VRAM is managed by hand anyway
  (model quantisation, `num_ctx`, transcode concurrency), it is pure ceremony.
- **MIG** is unavailable — Turing does not support it.

**Revisit this** if a second GPU node appears, if many GPU pods need scheduling, or if
anything schedules onto the cluster autonomously. Without the plugin, Kubernetes does not
know the GPU exists, so nothing prevents a third GPU pod landing on the node and OOMing the
others.

##### Measured cost of a 4K HDR transcode

Benchmarked 2026-08-23 on a real library file (2160p HEVC 10-bit HDR → 1080p SDR H.264,
full `NVDEC → tonemap_cuda → scale_cuda → h264_nvenc` chain, preset `p4`):

| Metric | Value |
|---|---|
| Throughput | **11.3x realtime** (272 fps) |
| VRAM | **859 MiB** |
| NVENC utilisation | 85% |
| NVDEC utilisation | 46% |
| GPU compute (tone-map) | 43% |

4K HDR is not a pure fixed-function workload — on NVIDIA, **CUDA is Jellyfin's only
tone-mapping method**, so HDR→SDR draws CUDA memory from the same pool as any AI workload.
At ~0.86 GB per stream, 8 GB leaves comfortable room for a ~4 GB model alongside one or two
concurrent transcodes.

The practical ceiling is NVENC throughput, not VRAM. Concurrent sessions are not a
constraint either: the consumer cap is 8 given Linux driver ≥ 550.54.14 and node-nv1 runs
595.84, but TU104 has a single NVENC unit so throughput saturates first.

##### Jellyfin application settings (Dashboard → Playback → Transcoding)

The manifest only grants access to the card — Jellyfin still has to be told to use it. These
live in `encoding.xml` on the config PVC:

| Setting | Value | Note |
|---|---|---|
| `HardwareAccelerationType` | `nvenc` | Was `qsv`. Wrong value transcodes on **CPU** and still "works", just slowly |
| `EnableTonemapping` | `true` | Required for 4K HDR; off means washed-out colour or software fallback |
| `HardwareDecodingCodecs` | h264, hevc, vc1, mpeg2video, vp9 | Turing NVDEC supports all of these |
| `EnableEnhancedNvdecDecoder` | `true` | Required for Dolby Vision |
| `EnableVppTonemapping` | `false` | Intel VPP path — must stay off on NVIDIA |
| `EnableDecodingColorDepth10Hevc` | `true` | 4K HDR is HEVC 10-bit |
| `AllowAv1Encoding` | `false` | See below |
| `EnableDecodingColorDepth10/12HevcRext` | `false` | Turing cannot decode 4:4:4 RExt |

Edit through the web UI, not the file — Jellyfin holds this config in memory and rewrites
`encoding.xml` on save, silently discarding external edits.

##### Turing codec limits

`ffmpeg -encoders` lists `av1_nvenc` and Jellyfin logs it as available. **This is misleading**
— ffmpeg reports what it was compiled with, not what the silicon supports. Turing has no AV1
encoder (Ada/RTX 40) and no AV1 decoder (Ampere/RTX 30). `AllowAv1Encoding: false` is what
actually prevents runtime failures.

Consequence for the library: AV1 source files decode on **CPU** on this node. If a transcode
performs badly, check the source codec before suspecting the GPU config.

##### Codec preference

Leave it on negotiation. `AllowHevcEncoding: true` means "use HEVC when the client advertises
support" — the correct setting. Do not force HEVC globally: the most common reason a
transcode happens at all is a client that *cannot* decode HEVC, so forcing it breaks exactly
the clients that needed help. Turing's HEVC encoder is materially better than its H.264 one
(7th-gen NVENC added HEVC B-frames), so capable clients already get the better path
automatically.

##### `NVIDIA_DRIVER_CAPABILITIES` is the easy one to miss

It defaults to `utility` in many setups, which yields a **working `nvidia-smi` inside the pod
while NVENC and the CUDA tone-mapper both fail** — a genuinely confusing combination, since
every obvious check passes. `all` (or explicitly `compute,video,utility`) is required:
`video` for NVENC/NVDEC, `compute` for tone-mapping.

##### What actually blocked the move

Not the GPU config — **NFS**. Every TrueNAS share's host ACL listed `172.31.0.10/.11/.12`
and node-nv1 is `.18`, so both the config PVC and `/mnt/storage0/media` were refused with
`access denied by server` and the pod never started. See the NFS allowed-hosts note in
[storage.md](storage.md) and `bootstrap/fix-nfs-share-hosts.py`. Fix share ACLs *before*
moving a workload to a new node.

Two leftovers from the Intel era, deliberately kept:

- The `devdri` hostPath (`hostPathType: Directory` on `/dev/dri`) still resolves on node-nv1
  (`renderD128` exists), so it is harmless — but it is only needed for the Intel path and can
  be dropped.
- `supplementalGroups` lists `109` and `568`. The `render` group is GID **993** on node-nv1,
  not 109. The container runs `privileged: true`, so device access does not depend on it.

##### Verifying the GPU is really being used

Jellyfin only transcodes when a client cannot direct-play — demanding content alone will
**not** touch the GPU. Force a transcode by lowering quality in the player, then:

```
kubectl exec -n mediabox deploy/jellyfin -- nvidia-smi
```

Idle is ~17 MiB. A live 4K HDR transcode shows ~860 MiB with encoder/decoder utilisation
non-zero. If VRAM stays at idle while the playback overlay says *Transcoding*, it is silently
on CPU — check the overlay names a hardware encoder rather than `libx264`.

To test the full pipeline without a client:

```
kubectl exec -n mediabox deploy/jellyfin -- /usr/lib/jellyfin-ffmpeg/ffmpeg -stats \
  -hwaccel cuda -hwaccel_output_format cuda -i "<4K HDR file>" -t 60 \
  -vf "tonemap_cuda=format=yuv420p:matrix=bt709:primaries=bt709:transfer=bt709,scale_cuda=1920:-2" \
  -c:v h264_nvenc -preset p4 -an -f null -
```

### Recyclarr

Recyclarr is a tool that synchronizes recommended settings from the TRaSH guides to Sonarr and Radarr.

#### Configuration

- Runs as a CronJob
- Configures quality profiles, custom formats, and release profiles

## Storage

The media stack uses persistent storage for both configuration and media content:

- **Configuration**: Each application has its own PVC for storing configuration
- **Databases**: Sonarr, Radarr, Bazarr, and Prowlarr each use a dedicated CloudNativePG (CNPG) PostgreSQL cluster instead of an embedded database on the config PVC
- **Media**: Shared NFS storage is used for media content, with separate directories for TV shows, movies, and downloads

## Networking

The media stack is exposed through the external Traefik instance:

- Each application has its own subdomain (e.g., sonarr.layertwo.dev)
- Authentication is handled by Pocket ID via an OIDC Traefik Middleware (`mediabox-oidc`)

## Maintenance

### Updating

Chart versions and image tags are pinned exactly rather than tracking a floating tag. Updates are proposed by Renovate bot as pull requests; once a PR is merged, Flux CD picks up the new pinned version and applies it.

### Backup

- There is no VolSync (or other automated) backup configured for any mediabox application's configuration
- Media content backup depends on the underlying NFS storage, not any in-cluster process

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
