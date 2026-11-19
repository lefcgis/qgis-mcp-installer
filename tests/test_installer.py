"""Pruebas unitarias del instalador (solo librería estándar).

    python -m unittest discover -s tests -v

Cubren la lógica pura: la que se puede romper sin que nadie lo note hasta que
falla en la PC de otra persona (edición del INI de QGIS, fusión del config de
Claude, selección de perfiles, catálogo de mensajes).
"""

from __future__ import annotations

import json
import os
import re
import string
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import etl_installer as etl  # noqa: E402
import manifest  # noqa: E402
from messages import MSG  # noqa: E402


class Mensajes(unittest.TestCase):
    def test_cada_clave_tiene_es_y_pt_con_los_mismos_marcadores(self):
        fmt = string.Formatter()
        for key, entry in MSG.items():
            self.assertEqual(set(entry), {"es", "pt"}, key)
            campos = [{f for _, f, _, _ in fmt.parse(entry[lang]) if f}
                      for lang in ("es", "pt")]
            self.assertEqual(campos[0], campos[1], key)

    def test_toda_clave_usada_en_el_codigo_existe(self):
        src = (ROOT / "etl_installer.py").read_text(encoding="utf-8")
        usadas = set(re.findall(r'\bT\(\s*"([a-z0-9_.]+)"', src))
        self.assertTrue(usadas)
        self.assertEqual(usadas - set(MSG), set())
        for n in etl.ALL_STEPS:
            self.assertIn(f"lbl.{n}", MSG)

    def test_no_quedan_claves_huerfanas(self):
        src = (ROOT / "etl_installer.py").read_text(encoding="utf-8")
        usadas = set(re.findall(r'"([a-z0-9]+\.[a-z0-9_]+)"', src))
        dinamicas = {k for k in MSG if k.startswith(("lbl.", "ui.next"))}
        self.assertEqual(set(MSG) - usadas - dinamicas, set())


class Pasos(unittest.TestCase):
    def test_parse_steps(self):
        self.assertEqual(etl.parse_steps(""), set(etl.ALL_STEPS))
        self.assertEqual(etl.parse_steps("4,5,6"), {4, 5, 6})
        self.assertEqual(etl.parse_steps("3-7"), {3, 4, 5, 6, 7})
        self.assertEqual(etl.parse_steps(" 1 , 7 "), {1, 7})

    def test_parse_steps_rechaza_invalidos(self):
        for malo in ("0", "8", "4,9", "x", "-"):
            with self.assertRaises(ValueError, msg=malo):
                etl.parse_steps(malo)

    def test_todos_los_pasos_tienen_funcion(self):
        self.assertEqual(set(etl.STEPS), set(etl.ALL_STEPS))


class Versiones(unittest.TestCase):
    def test_version_tuple(self):
        self.assertEqual(etl._version_tuple("3.44.12"), (3, 44, 12))
        self.assertEqual(etl._version_tuple("5.1231.2.0"), (5, 1231, 2, 0))
        self.assertEqual(etl._version_tuple(None), ())
        self.assertEqual(etl._version_tuple("no sé"), ())
        # el orden como texto pondría 3.44.9 por encima de 3.44.12
        self.assertGreater(etl._version_tuple("3.44.12"), etl._version_tuple("3.44.9"))


class Procesos(unittest.TestCase):
    def test_el_propio_instalador_no_cuenta_como_qgis_abierto(self):
        for nombre in ("qgis-bin.exe", "qgis-ltr-bin.exe", "QGIS-LTR-BIN.EXE",
                       "qgis-qt6-bin.exe"):
            self.assertTrue(etl.QGIS_IMAGE_RE.match(nombre), nombre)
        for nombre in ("qgis-mcp-installer.exe", "qgis_process-qgis-ltr.exe",
                       "qgis-ltr-bin.exe.bak"):
            self.assertFalse(etl.QGIS_IMAGE_RE.match(nombre), nombre)


class IniDeQgis(unittest.TestCase):
    P = "qgis_mcp_plugin"

    def test_ini_vacio(self):
        out = etl.enable_plugin_in_ini_text("", self.P)
        self.assertEqual(out, "[PythonPlugins]\nqgis_mcp_plugin=true\n")
        self.assertTrue(etl.plugin_enabled_in_ini_text(out, self.P))

    def test_sin_seccion_la_agrega_al_final(self):
        src = "[UI]\nlastProjectDir=C:/datos\n"
        out = etl.enable_plugin_in_ini_text(src, self.P)
        self.assertTrue(out.startswith(src))
        self.assertTrue(etl.plugin_enabled_in_ini_text(out, self.P))

    def test_con_seccion_inserta_sin_tocar_lo_demas(self):
        src = ("[PythonPlugins]\nprocessing=true\ndb_manager=true\n\n"
               "[qgis]\nproj/crs/EPSG:4326=x\nfmt=%1 de %2\nUI\\recent\\1\\path=C:/a b.qgz\n")
        out = etl.enable_plugin_in_ini_text(src, self.P)
        self.assertTrue(etl.plugin_enabled_in_ini_text(out, self.P))
        # Solo se añadió UNA línea; el resto queda byte a byte.
        quitada = out.replace("qgis_mcp_plugin=true\n", "", 1)
        self.assertEqual(quitada, src)

    def test_false_pasa_a_true(self):
        src = "[PythonPlugins]\nqgis_mcp_plugin=false\nprocessing=true\n"
        out = etl.enable_plugin_in_ini_text(src, self.P)
        self.assertEqual(out, "[PythonPlugins]\nqgis_mcp_plugin=true\nprocessing=true\n")

    def test_idempotente(self):
        una = etl.enable_plugin_in_ini_text("[PythonPlugins]\nprocessing=true\n", self.P)
        self.assertEqual(etl.enable_plugin_in_ini_text(una, self.P), una)

    def test_conserva_crlf(self):
        src = "[PythonPlugins]\r\nprocessing=true\r\n"
        out = etl.enable_plugin_in_ini_text(src, self.P)
        self.assertNotIn("\n", out.replace("\r\n", ""))
        self.assertTrue(etl.plugin_enabled_in_ini_text(out, self.P))

    def test_no_parte_valores_con_caracteres_de_control(self):
        # splitlines() cortaría en un retorno de carro suelto, \x0c o \x1c
        src = ("[PythonPlugins]\r\nprocessing=true\r\n\r\n[qgis]\r\n"
               "raro=a\rb\x0cc\x1cd\x01e\r\nfin=1\r\n")
        out = etl.enable_plugin_in_ini_text(src, self.P)
        self.assertEqual(out.replace("qgis_mcp_plugin=true\r\n", "", 1), src)

    def test_archivo_sin_salto_final(self):
        out = etl.enable_plugin_in_ini_text("[UI]\na=1", self.P)
        self.assertEqual(out, "[UI]\na=1\n\n[PythonPlugins]\nqgis_mcp_plugin=true\n")
        out = etl.enable_plugin_in_ini_text("[PythonPlugins]", self.P)
        self.assertEqual(out, "[PythonPlugins]\nqgis_mcp_plugin=true\n")

    def test_autostart_en_seccion_propia_sin_tocar_lo_demas(self):
        src = "[PythonPlugins]\nqgis_mcp_plugin=true\n\n[qgis_mcp]\nport=9876\nfirst_run=false\n"
        out = etl.set_ini_value(src, "qgis_mcp", "autostart", "true")
        self.assertEqual(out.replace("autostart=true\n", "", 1), src)
        self.assertEqual(etl.set_ini_value(out, "qgis_mcp", "autostart", "true"), out)
        nuevo = etl.set_ini_value("[PythonPlugins]\nqgis_mcp_plugin=true\n",
                                  "qgis_mcp", "autostart", "true")
        self.assertEqual(nuevo, "[PythonPlugins]\nqgis_mcp_plugin=true\n\n"
                                "[qgis_mcp]\nautostart=true\n")

    def test_no_confunde_la_clave_en_otra_seccion(self):
        src = "[Otra]\nqgis_mcp_plugin=true\n[PythonPlugins]\nprocessing=true\n"
        self.assertFalse(etl.plugin_enabled_in_ini_text(src, self.P))
        out = etl.enable_plugin_in_ini_text(src, self.P)
        self.assertTrue(etl.plugin_enabled_in_ini_text(out, self.P))
        self.assertEqual(out.count("qgis_mcp_plugin=true"), 2)


class ConfigDeClaude(unittest.TestCase):
    ENTRY = {"command": r"C:\x\python\python.exe",
             "args": ["-I", r"C:\x\env\run_server.py"]}

    def test_config_nuevo(self):
        out, invalido = etl.merge_claude_config(None, self.ENTRY)
        self.assertFalse(invalido)
        self.assertEqual(json.loads(out), {"mcpServers": {"qgis": self.ENTRY}})

    def test_conserva_otros_servidores_y_preferencias(self):
        previo = json.dumps({
            "preferences": {"tema": "oscuro"},
            "mcpServers": {"otro": {"command": "x"}, "qgis": {"command": "viejo"}},
        })
        data = json.loads(etl.merge_claude_config(previo, self.ENTRY)[0])
        self.assertEqual(data["preferences"], {"tema": "oscuro"})
        self.assertEqual(data["mcpServers"]["otro"], {"command": "x"})
        self.assertEqual(data["mcpServers"]["qgis"], self.ENTRY)

    def test_json_invalido_se_reporta(self):
        out, invalido = etl.merge_claude_config("{esto no es json", self.ENTRY)
        self.assertTrue(invalido)
        self.assertEqual(json.loads(out)["mcpServers"]["qgis"], self.ENTRY)

    def test_archivo_vacio_no_es_error(self):
        out, invalido = etl.merge_claude_config("  \n", self.ENTRY)
        self.assertFalse(invalido)
        self.assertIn("qgis", json.loads(out)["mcpServers"])

    def test_quitar_la_entrada(self):
        previo = json.dumps({"mcpServers": {"otro": {"command": "x"}, "qgis": self.ENTRY}})
        data = json.loads(etl.merge_claude_config(previo, None)[0])
        self.assertEqual(data["mcpServers"], {"otro": {"command": "x"}})

    def test_config_con_bom_no_pierde_los_otros_servidores(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claude_desktop_config.json"
            path.write_text(json.dumps({"mcpServers": {"otro": {"command": "x"}}}),
                            encoding="utf-8-sig")
            log = etl.Logger(Path(tmp) / "x.log", to_file=False)
            with mock.patch("builtins.print"):
                etl._write_claude_config(path, self.ENTRY, log)
            raw = path.read_bytes()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            data = json.loads(raw.decode("utf-8"))
            self.assertEqual(set(data["mcpServers"]), {"otro", "qgis"})
            self.assertEqual(len(list(Path(tmp).glob("*.bak-*"))), 1)


class Rutas(unittest.TestCase):
    def _cfg(self, base: Path, **kw) -> etl.Config:
        return etl.Config(base_dir=base, qgis_profile=kw.pop("profile", "auto"),
                          steps=set(etl.ALL_STEPS), dry_run=False,
                          non_interactive=True, skip_signature=False,
                          plugin_url="", **kw)

    def test_perfil_activo_segun_profiles_ini(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "Roaming"
            perfiles = app / "QGIS" / "QGIS3" / "profiles"
            for nombre in ("default", "trabajo", "workshop"):
                (perfiles / nombre).mkdir(parents=True)
            ini = perfiles / "profiles.ini"
            with mock.patch.dict(os.environ, {"APPDATA": str(app)}):
                cfg = self._cfg(Path(tmp) / "raiz")

                def destinos():
                    return [p.name for _, p in cfg.qgis_targets()]

                self.assertEqual(destinos(), ["default"])  # sin profiles.ini
                # política 0 (por defecto): el último perfil usado
                ini.write_text("[core]\nselectionPolicy=0\nlastProfile=workshop\n",
                               encoding="utf-8")
                self.assertEqual(destinos(), ["workshop"])
                # política 1: el perfil fijo, aunque el último sea otro
                ini.write_text("[core]\nselectionPolicy=1\nlastProfile=workshop\n"
                               "defaultProfile=trabajo\n", encoding="utf-8")
                self.assertEqual(destinos(), ["trabajo"])
                # política 2 (preguntar): todos
                ini.write_text("[core]\nselectionPolicy=2\n", encoding="utf-8")
                self.assertEqual(destinos(), ["default", "trabajo", "workshop"])
                # QGIS antiguo: solo defaultProfile
                ini.write_text("[core]\ndefaultProfile=trabajo\n", encoding="utf-8")
                self.assertEqual(destinos(), ["trabajo"])
                # un perfil que ya no existe no se usa
                ini.write_text("[core]\nselectionPolicy=0\nlastProfile=borrado\n",
                               encoding="utf-8")
                self.assertEqual(destinos(), ["default"])
                # un perfil explícito manda sobre profiles.ini
                cfg2 = self._cfg(Path(tmp) / "raiz", profile="otro")
                self.assertEqual([p.name for _, p in cfg2.qgis_targets()], ["otro"])

    def test_equipo_sin_qgis_usa_qgis3_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "Roaming"
            with mock.patch.dict(os.environ, {"APPDATA": str(app)}):
                cfg = self._cfg(Path(tmp) / "raiz")
                self.assertEqual(
                    cfg.qgis_targets(),
                    [("3", app / "QGIS" / "QGIS3" / "profiles" / "default")])

    def test_qgis3_y_qgis4_a_la_vez(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / "Roaming"
            (app / "QGIS" / "QGIS3").mkdir(parents=True)
            with mock.patch.dict(os.environ, {"APPDATA": str(app)}):
                cfg = self._cfg(Path(tmp) / "raiz")
                cfg.qgis_version = "4.2.3"
                self.assertEqual([m for m, _ in cfg.qgis_targets()], ["3", "4"])

    def test_config_de_claude_clasico_y_msix_virtualizado(self):
        with tempfile.TemporaryDirectory() as tmp:
            app, local = Path(tmp) / "Roaming", Path(tmp) / "Local"
            nombre = "claude_desktop_config.json"
            with mock.patch.dict(os.environ, {"APPDATA": str(app),
                                              "LOCALAPPDATA": str(local)}):
                cfg = self._cfg(Path(tmp) / "raiz")
                self.assertEqual(cfg.claude_config_paths(), [app / "Claude" / nombre])
                virt = (local / "Packages" / manifest.CLAUDE_MSIX_FAMILY
                        / "LocalCache" / "Roaming" / "Claude")
                virt.mkdir(parents=True)
                # Claude-Data solo cuenta si YA tiene un config dentro
                (local / "Claude-Data" / "x").mkdir(parents=True)
                self.assertEqual(cfg.claude_config_paths(),
                                 [app / "Claude" / nombre, virt / nombre])
                (local / "Claude-Data" / "x" / nombre).write_text("{}", encoding="utf-8")
                self.assertEqual(len(cfg.claude_config_paths()), 3)

    def test_entrada_del_servidor_usa_rutas_absolutas_y_no_un_venv(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._cfg(Path(tmp) / "raíz con espacios")
            self.assertIsNone(etl.server_entry(cfg))  # sin Python aún no hay entrada
            exe = "python.exe" if etl.IS_WIN else "bin/python3"
            for ver in ("3.12.9", "3.12.16"):
                py = cfg.python_dir / f"cpython-{ver}-windows-x86_64-none" / exe
                py.parent.mkdir(parents=True)
                py.write_bytes(b"")
            entry = etl.server_entry(cfg)
            # la más reciente por número, no la "mayor" como texto (9 > 16)
            self.assertIn("3.12.16", entry["command"])
            self.assertTrue(Path(entry["command"]).is_absolute())
            self.assertEqual(entry["args"], ["-I", str(cfg.launcher)])
            self.assertNotIn("Scripts", entry["command"])

    def test_el_lanzador_compila_y_no_lleva_rutas_del_equipo(self):
        compile(etl.LAUNCHER_SOURCE, "run_server.py", "exec")
        self.assertNotIn(":\\", etl.LAUNCHER_SOURCE)
        self.assertIn("site.addsitedir", etl.LAUNCHER_SOURCE)


class Manifiesto(unittest.TestCase):
    def test_descargas_por_https_y_claves_unicas(self):
        self.assertEqual(len(manifest.DOWNLOADS), 6)
        for dl in manifest.DOWNLOADS.values():
            self.assertTrue(dl.url.startswith("https://"), dl.key)
            self.assertTrue(dl.filename, dl.key)

    def test_lo_que_se_ejecuta_tiene_firma_o_hash(self):
        for key in ("claude_setup", "qgis_ltr", "osgeo4w_setup", "uv"):
            dl = manifest.DOWNLOADS[key]
            self.assertTrue(dl.expected_publisher_contains or dl.sha256, key)
        self.assertRegex(manifest.UV.sha256 or "", r"^[0-9a-f]{64}$")
        self.assertIn(manifest.UV_VERSION, manifest.UV.url)


class Arranque(unittest.TestCase):
    def test_instalar_cmd_usa_la_misma_version_y_hash_de_uv_que_el_manifiesto(self):
        raw = (ROOT / "instalar.cmd").read_bytes()
        texto = raw.decode("ascii")  # sin tildes: cmd.exe las rompe según la página de códigos
        self.assertIn(f'set "UV_VERSION={manifest.UV_VERSION}"', texto)
        self.assertIn(f'set "UV_SHA256={manifest.UV.sha256}"', texto)
        self.assertIn(f'set "PY_VERSION={manifest.PYTHON_VERSION}"', texto)
        # los .cmd con saltos LF sueltos fallan en los goto/call
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
