import json
from pathlib import Path
import uuid
import datetime
import shutil

class OverlayService:
    def __init__(self):
        self.sets = []
        data_dir = Path.home() / '.local' / 'share' / 'atomicbasejump'
        data_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = data_dir / 'overlay_sets.json'
        self.loadFromFile()

    def getOverlaySet(self, id):
        for s in self.sets:
            if s.get("id") == id:
                return s
        return None

    def _processLocalPackages(self, localPackages):
        result = []
        data_dir = Path.home() / '.local' / 'share' / 'atomicbasejump' / 'local_rpms'
        data_dir.mkdir(parents=True, exist_ok=True)
        for pkg in localPackages:
            path = pkg.strip()
            if path.startswith("file://"):
                path = path[7:]
            fi = Path(path)
            if fi.exists():
                destPath = data_dir / fi.name
                if fi.resolve() != destPath.resolve():
                    try:
                        if destPath.exists():
                            destPath.unlink()
                        shutil.copy2(path, destPath)
                        destPath.chmod(0o644)
                        path = str(destPath)
                    except Exception:
                        pass
                else:
                    path = str(destPath)
            result.append(path)
        return result

    def createOverlaySet(self, name, description, layeredPackages, localPackages, removedPackages):
        set_id = "overlay_" + str(uuid.uuid4().hex)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        new_set = {
            "id": set_id,
            "name": name.strip() if name.strip() else "Unnamed Overlay Set",
            "description": description.strip(),
            "createdAt": now,
            "updatedAt": now,
            "layeredPackages": layeredPackages,
            "localPackages": self._processLocalPackages(localPackages),
            "removedPackages": removedPackages
        }
        self.sets.append(new_set)
        self.saveToFile()
        return set_id

    def updateOverlaySet(self, id, name, description, layeredPackages, localPackages, removedPackages):
        for s in self.sets:
            if s.get("id") == id:
                s["name"] = name.strip()
                s["description"] = description.strip()
                s["updatedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                s["layeredPackages"] = layeredPackages
                s["localPackages"] = self._processLocalPackages(localPackages)
                s["removedPackages"] = removedPackages
                self.saveToFile()
                return True
        return False

    def deleteOverlaySet(self, id):
        for i, s in enumerate(self.sets):
            if s.get("id") == id:
                self.sets.pop(i)
                self.saveToFile()
                return True
        return False

    def exportJson(self):
        return json.dumps(self.sets, indent=2)

    def importJson(self, jsonString):
        try:
            data = json.loads(jsonString)
            if not isinstance(data, list):
                return False
            importedAny = False
            existing_ids = {s.get("id") for s in self.sets}
            for val in data:
                if isinstance(val, dict) and "name" in val:
                    if not val.get("id") or val["id"] in existing_ids:
                        val["id"] = "overlay_" + str(uuid.uuid4().hex)
                    existing_ids.add(val["id"])
                    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    if "createdAt" not in val:
                        val["createdAt"] = now
                    val["updatedAt"] = now

                    val["layeredPackages"] = val.get("layeredPackages", [])
                    val["localPackages"] = self._processLocalPackages(val.get("localPackages", []))
                    val["removedPackages"] = val.get("removedPackages", [])

                    self.sets.append(val)
                    importedAny = True
            if importedAny:
                self.saveToFile()
            return importedAny
        except Exception:
            return False

    def loadFromFile(self):
        self.sets = []
        if self._file_path.exists():
            try:
                with open(self._file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.sets = data
            except Exception:
                pass

    def saveToFile(self):
        try:
            with open(self._file_path, 'w') as f:
                json.dump(self.sets, f, indent=2)
        except Exception:
            pass
