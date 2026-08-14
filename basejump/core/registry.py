import json
import re
import threading

import requests

class ImageRegistryService:
    def __init__(self):
        self.loading_tags = False
        self.loading_build_date = False

    @staticmethod
    def _registry_parts(image_ref):
        image_ref = image_ref.removeprefix("docker://")
        registry, _, repository = image_ref.partition("/")
        if "." not in registry and ":" not in registry and registry != "localhost":
            registry, repository = "registry-1.docker.io", image_ref
        return registry, repository

    def _request(self, image_ref, path, accept=None):
        registry, repository = self._registry_parts(image_ref)
        headers = {"Accept": accept} if accept else {}
        base = f"https://{registry}"
        response = requests.get(base + path.format(repository=repository), headers=headers, timeout=15)
        if response.status_code == 401:
            auth = response.headers.get("WWW-Authenticate", "")
            match = re.match(r'Bearer realm="([^"]+)",service="([^"]+)",scope="([^"]+)"', auth)
            if match:
                token = requests.get(
                    match.group(1), params={"service": match.group(2), "scope": match.group(3)}, timeout=15
                ).json()["token"]
                headers["Authorization"] = f"Bearer {token}"
                response = requests.get(base + path.format(repository=repository), headers=headers, timeout=15)
        response.raise_for_status()
        return response

    @staticmethod
    def _classify_tags(tags):
        """Separate user-facing streams and releases from registry build tags."""
        versions = sorted({
            tag for tag in tags
            if tag.isdigit() or ("-" in tag and tag.split("-", 1)[1].isdigit())
        })
        version_set = set(versions)
        streams = []
        for tag in tags:
            # Fedora publishes dated builds and architecture-specific aliases
            # alongside the release and stream tags in the same repository.
            is_dated_build = re.fullmatch(r"\d+\.\d{8}\.\d+(?:-.+)?", tag)
            is_architecture_tag = re.fullmatch(r"\d+-(?:[A-Za-z0-9_]+)", tag)
            if tag in version_set or is_dated_build or is_architecture_tag:
                continue
            streams.append(tag)
        return streams, versions

    def fetchTags(self, image_ref, on_success, on_error):
        self.loading_tags = True

        def worker():
            try:
                data = self._request(image_ref, "/v2/{repository}/tags/list").json()
                tags = [tag for tag in data.get("tags", []) if not tag.startswith("sha256-") and not tag.endswith(".sig")]
                streams, versions = self._classify_tags(tags)
                date_tags = [tag for tag in tags if re.search(r"\d{8}", tag)]
                on_success(image_ref, streams, versions, date_tags)
            except Exception as error:
                on_error(image_ref, str(error))
            finally:
                self.loading_tags = False

        threading.Thread(target=worker, daemon=True).start()

    def fetchTagBuildDate(self, image_ref, tag, on_success, on_error):
        self.loading_build_date = True

        def worker():
            try:
                manifest = self._request(
                    image_ref,
                    f"/v2/{{repository}}/manifests/{tag}",
                    "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json",
                ).json()
                if "manifests" in manifest:
                    target = next((item for item in manifest["manifests"] if item.get("platform", {}).get("architecture") == "amd64"), manifest["manifests"][0])
                    digest = target["digest"]
                    manifest = self._request(image_ref, f"/v2/{{repository}}/manifests/{digest}", "application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json").json()
                config = self._request(image_ref, f"/v2/{{repository}}/blobs/{manifest['config']['digest']}").json()
                on_success(image_ref, tag, config.get("created", "Unknown").split("T")[0])
            except Exception as error:
                on_error(image_ref, tag, str(error))
            finally:
                self.loading_build_date = False

        threading.Thread(target=worker, daemon=True).start()

    def sources(self):
        return [
            {
                "id": "fedora",
                "name": "Official Fedora",
                "description": "Official Fedora Project Atomic Desktops",
                "icon": "computer"
            },
            {
                "id": "ublue",
                "name": "Universal Blue",
                "description": "Community container images with desktop, gaming, and dev optimizations",
                "icon": "preferences-desktop"
            },
            {
                "id": "secureblue",
                "name": "Secureblue",
                "description": "Hardened Fedora Atomic images designed for security and privacy",
                "icon": "security-high"
            }
        ]

    def typesForSource(self, sourceId):
        types = []
        if sourceId == "fedora":
            types = [
                {"id": "fedora-kinoite", "name": "Fedora Kinoite", "description": "KDE Plasma Desktop environment built on Fedora Atomic base", "imageRef": "quay.io/fedora/fedora-kinoite", "desktopFamily": "plasma"},
                {"id": "fedora-silverblue", "name": "Fedora Silverblue", "description": "GNOME Desktop environment built on Fedora Atomic base", "imageRef": "quay.io/fedora/fedora-silverblue", "desktopFamily": "gnome"},
                {"id": "fedora-sericea", "name": "Fedora Sericea", "description": "Sway Wayland desktop environment built on Fedora Atomic base", "imageRef": "quay.io/fedora/fedora-sericea", "desktopFamily": "other"},
                {"id": "fedora-onyx", "name": "Fedora Onyx", "description": "Budgie Desktop environment built on Fedora Atomic base", "imageRef": "quay.io/fedora/fedora-onyx", "desktopFamily": "other"},
                {"id": "fedora-sway-atomic", "name": "Fedora Sway Atomic", "description": "Sway window manager Atomic desktop variant", "imageRef": "quay.io/fedora/fedora-sway-atomic", "desktopFamily": "other"},
                {"id": "fedora-budgie-atomic", "name": "Fedora Budgie Atomic", "description": "Budgie Atomic desktop variant", "imageRef": "quay.io/fedora/fedora-budgie-atomic", "desktopFamily": "other"},
                {"id": "fedora-coreos", "name": "Fedora CoreOS", "description": "Automatically updating, minimal container host", "imageRef": "quay.io/fedora/fedora-coreos", "desktopFamily": "other"}
            ]
        elif sourceId == "ublue":
            types = [
                {"id": "aurora", "name": "Aurora", "description": "KDE Plasma Developer Workstation with batteries included", "imageRef": "ghcr.io/ublue-os/aurora", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "aurora-nvidia-open", "name": "Aurora Nvidia Open", "description": "KDE Plasma Developer Workstation with open Nvidia drivers", "imageRef": "ghcr.io/ublue-os/aurora-nvidia-open", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "aurora-dx", "name": "Aurora DX", "description": "Developer Experience edition with containers, IDEs, and CLI tools", "imageRef": "ghcr.io/ublue-os/aurora-dx", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "aurora-dx-nvidia-open", "name": "Aurora DX Nvidia Open", "description": "Aurora DX with open Nvidia drivers", "imageRef": "ghcr.io/ublue-os/aurora-dx-nvidia-open", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "bazzite", "name": "Bazzite", "description": "Gaming Workstation with KDE Plasma desktop & gaming tweaks", "imageRef": "ghcr.io/ublue-os/bazzite", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "bazzite-deck", "name": "Bazzite Deck", "description": "Handheld Gaming OS tailored for Steam Deck and handheld consoles", "imageRef": "ghcr.io/ublue-os/bazzite-deck", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "bazzite-nvidia-open", "name": "Bazzite Nvidia Open", "description": "Gaming Workstation with KDE Plasma & open Nvidia graphics drivers", "imageRef": "ghcr.io/ublue-os/bazzite-nvidia-open", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "bazzite-gnome", "name": "Bazzite GNOME", "description": "Gaming Workstation with GNOME desktop environment", "imageRef": "ghcr.io/ublue-os/bazzite-gnome", "desktopFamily": "gnome", "supportsSignatureChoice": True},
                {"id": "bazzite-gnome-nvidia-open", "name": "Bazzite GNOME Nvidia Open", "description": "Bazzite GNOME with open Nvidia drivers", "imageRef": "ghcr.io/ublue-os/bazzite-gnome-nvidia-open", "desktopFamily": "gnome", "supportsSignatureChoice": True},
                {"id": "bluefin", "name": "Bluefin", "description": "GNOME Developer Workstation built for productivity", "imageRef": "ghcr.io/ublue-os/bluefin", "desktopFamily": "gnome", "supportsSignatureChoice": True},
                {"id": "bluefin-nvidia-open", "name": "Bluefin Nvidia Open", "description": "GNOME Developer Workstation with open Nvidia drivers", "imageRef": "ghcr.io/ublue-os/bluefin-nvidia-open", "desktopFamily": "gnome", "supportsSignatureChoice": True},
                {"id": "bluefin-dx", "name": "Bluefin DX", "description": "GNOME Developer Experience edition with dev tools preinstalled", "imageRef": "ghcr.io/ublue-os/bluefin-dx", "desktopFamily": "gnome", "supportsSignatureChoice": True},
                {"id": "bluefin-dx-nvidia-open", "name": "Bluefin DX Nvidia Open", "description": "Bluefin DX with open Nvidia drivers", "imageRef": "ghcr.io/ublue-os/bluefin-dx-nvidia-open", "desktopFamily": "gnome", "supportsSignatureChoice": True},
                {"id": "kinoite-main", "name": "Kinoite Main", "description": "Stock Fedora Kinoite with uBlue core fixes & codecs", "imageRef": "ghcr.io/ublue-os/kinoite-main", "desktopFamily": "plasma", "supportsSignatureChoice": True},
                {"id": "silverblue-main", "name": "Silverblue Main", "description": "Stock Fedora Silverblue with uBlue core fixes & codecs", "imageRef": "ghcr.io/ublue-os/silverblue-main", "desktopFamily": "gnome", "supportsSignatureChoice": True},
                {"id": "sway-main", "name": "Sway Main", "description": "Stock Fedora Sway with uBlue core fixes", "imageRef": "ghcr.io/ublue-os/sway-main", "desktopFamily": "other", "supportsSignatureChoice": True}
            ]
        elif sourceId == "secureblue":
            types = [
                {"id": "kinoite-main-userns", "name": "Secureblue Kinoite", "description": "Hardened Fedora KDE Plasma with user namespace hardening", "imageRef": "ghcr.io/secureblue/kinoite-main-userns", "desktopFamily": "plasma"},
                {"id": "silverblue-main-userns", "name": "Secureblue Silverblue", "description": "Hardened Fedora GNOME with user namespace hardening", "imageRef": "ghcr.io/secureblue/silverblue-main-userns", "desktopFamily": "gnome"},
                {"id": "sericea-main-userns", "name": "Secureblue Sericea", "description": "Hardened Fedora Sway with user namespace hardening", "imageRef": "ghcr.io/secureblue/sericea-main-userns", "desktopFamily": "other"},
                {"id": "kinoite-nvidia-userns", "name": "Secureblue Kinoite Nvidia", "description": "Hardened Fedora KDE Plasma with Nvidia drivers & hardening", "imageRef": "ghcr.io/secureblue/kinoite-nvidia-userns", "desktopFamily": "plasma"},
                {"id": "silverblue-nvidia-userns", "name": "Secureblue Silverblue Nvidia", "description": "Hardened Fedora GNOME with Nvidia drivers & hardening", "imageRef": "ghcr.io/secureblue/silverblue-nvidia-userns", "desktopFamily": "gnome"}
            ]
        return types

    def stripTransportPrefix(self, s):
        prefixes = [
            "ostree-image-signed:docker://",
            "ostree-unverified-image:docker://",
            "ostree-unverified-registry:",
            "ostree-remote-image:",
            "docker://"
        ]
        s = s.strip()
        for p in prefixes:
            if s.startswith(p):
                return s[len(p):]
        return s

    def imageRefFromRefspec(self, refspec):
        s = self.stripTransportPrefix(refspec.strip())
        if not s:
            return ""
        at_idx = s.find('@')
        if at_idx >= 0:
            s = s[:at_idx]
        colon_idx = s.rfind(':')
        slash_idx = s.rfind('/')
        if colon_idx > slash_idx:
            s = s[:colon_idx]
        return s

    def tagFromRefspec(self, refspec):
        s = self.stripTransportPrefix(refspec.strip())
        if not s:
            return ""
        at_idx = s.find('@')
        if at_idx >= 0:
            s = s[:at_idx]
        colon_idx = s.rfind(':')
        slash_idx = s.rfind('/')
        if colon_idx > slash_idx:
            return s[colon_idx + 1:]
        return ""

    def isStreamTag(self, tag):
        tag = tag.strip()
        if not tag:
            return False
        known_streams = ["latest", "stable", "beta", "testing", "gts", "lts", "rawhide", "unstable", "stable-daily", "stream9", "stream10"]
        first_part = tag.split('-')[0].lower()
        lower = tag.lower()
        if lower in known_streams:
            return True
        return first_part in known_streams

    def matchImageRef(self, imageRefOrRefspec):
        result = {
            "found": False,
            "sourceId": "",
            "sourceIndex": -1,
            "typeIndex": -1,
            "imageRef": ""
        }
        path = self.imageRefFromRefspec(imageRefOrRefspec)
        if not path:
            path = imageRefOrRefspec.strip()
        if not path:
            return result
        
        srcs = self.sources()
        for si, src in enumerate(srcs):
            sourceId = src.get("id")
            types = self.typesForSource(sourceId)
            for ti, typ in enumerate(types):
                catalogRef = typ.get("imageRef", "")
                if catalogRef.lower() == path.lower():
                    result["found"] = True
                    result["sourceId"] = sourceId
                    result["sourceIndex"] = si
                    result["typeIndex"] = ti
                    result["imageRef"] = catalogRef
                    return result
        return result

    def resolveBootedSelection(self, refspec):
        result = self.matchImageRef(refspec)
        tag = self.tagFromRefspec(refspec)
        result["tag"] = tag
        result["useVersionTag"] = bool(tag) and not self.isStreamTag(tag)
        result["signed"] = self.isSignedTransport(refspec)
        return result

    def constructRefSpec(self, imageRef, tag, requireSignature=True):
        tag = tag.strip()
        effectiveTag = tag if tag else "latest"
        image = imageRef.strip()
        if not image:
            return ""
        if requireSignature:
            return f"ostree-image-signed:docker://{image}:{effectiveTag}"
        return f"ostree-unverified-registry:{image}:{effectiveTag}"

    def desktopFamilyFromRef(self, refOrImage):
        refOrImage = refOrImage.strip()
        if not refOrImage:
            return "unknown"
        match = self.matchImageRef(refOrImage)
        if match.get("found"):
            sourceId = match.get("sourceId")
            typeIndex = match.get("typeIndex")
            types = self.typesForSource(sourceId)
            if 0 <= typeIndex < len(types):
                family = types[typeIndex].get("desktopFamily", "")
                if family:
                    return family
        
        path = self.imageRefFromRefspec(refOrImage)
        hay = path.lower() if path else refOrImage.lower()
        if any(x in hay for x in ["bazzite-gnome", "silverblue", "bluefin", "gnome"]):
            return "gnome"
        if any(x in hay for x in ["kinoite", "aurora", "bazzite"]):
            return "plasma"
        if any(x in hay for x in ["sericea", "sway", "budgie", "onyx", "coreos"]):
            return "other"
        return "unknown"
        
    def isUblueRef(self, refOrImage):
        image = self.imageRefFromRefspec(refOrImage)
        image = image if image else refOrImage.strip()
        return "ghcr.io/ublue-os/" in image.lower() or image.lower().startswith("ublue-os/")
        
    def allowsSignedUblueTarget(self, currentRefspec):
        return self.isUblueRef(currentRefspec)
        
    def isSignedTransport(self, refspec):
        return refspec.strip().startswith("ostree-image-signed:")
