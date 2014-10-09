from lxml import etree
from lxml.etree import Element, SubElement

import os
import os.path
import shutil
import subprocess
import copy

class CulturalImperialismException(Exception): pass

class Generator:
    def __init__(self, project):
        self._project = project

class AndroidGenerator(Generator):
    ANDROID_NS="http://schemas.android.com/apk/res/android"
    NS = "http://schemas.android.com/apk/res-auto"

    def _element(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k in ['keyLabel', 'additionalMoreKeys', 'keyHintLabel'] and\
                    v in ['#', '@']:
                v = '\\' + v
            o["{%s}%s" % (self.NS, k)] = v
        return Element(*args, **o)

    def _android_subelement(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k == 'keyLabel' and v in ['#', '@']:
                v = '\\' + v
            o["{%s}%s" % (self.ANDROID_NS, k)] = v
        return SubElement(*args, **o)

    def _subelement(self, *args, **kwargs):
        o = {}
        for k, v in kwargs.items():
            if k == 'keyLabel' and v in ['#', '@']:
                v = '\\' + v
            o["{%s}%s" % (self.NS, k)] = v
        return SubElement(*args, **o)

    def _tostring(self, tree):
        return etree.tostring(tree, pretty_print=True,
            xml_declaration=True, encoding='utf-8').decode()

    def generate(self, base='.', sdk_base='./sdk'):
        self.get_source_tree(base, sdk_base)

        styles = [
            ('phone', 'xml'),
            ('tablet', 'xml-sw600dp')
        ]

        files = []

        print(self._project.layouts)

        for name, kbd in self._project.layouts.items():

            files += [
                ('res/xml/keyboard_layout_set_%s.xml' % name, self.kbd_layout_set(kbd)),
                ('res/xml/kbd_%s.xml' % name, self.keyboard(kbd))
            ]

            for style, prefix in styles:
                self.gen_key_width(kbd, style)

                files.append(("res/%s/rows_%s.xml" % (prefix, name),
                    self.rows(kbd, style)))

                for row in self.rowkeys(kbd, style):
                    row = ("res/%s/%s" % (prefix, row[0]), row[1])
                    files.append(row)

            self.update_method_xml(kbd, base)
            self.update_strings_xml(kbd, base)

        self.save_files(files, base)

        self.update_localisation(base)

        self.build(base)

    def sanity_checks(self):
        pass #stub

    def _upd_locale(self, d, values):
        print("Updating localisation for %s..." % d)

        fn = os.path.join(d, "strings-appname.xml")
        node = None

        if os.path.exists(fn):
            with open(fn) as f:
                tree = etree.parse(f)
            nodes = tree.xpath("string[@name='english_ime_name']")
            if len(nodes) > 0:
                node = nodes[0]
        else:
            tree = etree.XML("<resources/>")

        if node is None:
            node = SubElement(tree, 'string', name="english_ime_name")

        node.text = values['name'].replace("'", r"\'")

        with open(fn, 'w') as f:
            f.write(self._tostring(tree))

    def update_localisation(self, base):
        res_dir = os.path.join(base, 'deps', 'sami-ime', 'res')

        self._upd_locale(os.path.join(res_dir, "values"),
            self._project.locales['en'])

        for locale, values in self._project.locales.items():
            d = os.path.join(res_dir, "values-%s" % locale)
            if os.path.isdir(d):
                self._upd_locale(d, values)

    def build(self, base, debug=True):
        self.sanity_checks()

        # TODO normal build
        print("Building...")
        process = subprocess.Popen(['ant', 'debug'], 
                    cwd=os.path.join(base, 'deps', 'sami-ime'))
        process.wait()

        fn = "SamiIME-debug.apk"
        path = os.path.join(base, 'deps', 'sami-ime', 'bin')

        print("Copying '%s' to build/ directory..." % fn)
        os.makedirs(os.path.join(base, 'build'), exist_ok=True)
        shutil.copy(os.path.join(path, fn), os.path.join(base, 'build'))

        print("Done!")

    def _str_xml(self, val_dir, name, subtype):
        if os.path.isdir(val_dir):
            fn = os.path.join(val_dir, 'strings.xml')

            print("Updating %s..." % fn)
            with open(fn) as f:
                tree = etree.parse(f)
                SubElement(tree.getroot(),
                    "string",
                    name="subtype_%s" % subtype)\
                    .text = name

            with open(fn, 'w') as f:
                f.write(self._tostring(tree))

    def update_strings_xml(self, kbd, base):
        # TODO sanity check for non-existence directories
        # TODO run this only once preferably
        res_dir = os.path.join(base, 'deps', 'sami-ime', 'res')

        for locale, name in kbd.display_names.items():
            if locale == "en":
                val_dir = os.path.join(res_dir, 'values')
            else:
                val_dir = os.path.join(res_dir, 'values-%s' % locale)
            self._str_xml(val_dir, name, kbd.internal_name)

    def update_method_xml(self, kbd, base):
        # TODO run this only once preferably
        print("Updating res/xml/method.xml...")
        fn = os.path.join(base, 'deps', 'sami-ime', 'res', 'xml', 'method.xml')

        with open(fn) as f:
            tree = etree.parse(f)

        self._android_subelement(tree.getroot(), 'subtype',
            icon="@drawable/ic_ime_switcher_dark",
            label="@string/subtype_%s" % kbd.internal_name,
            imeSubtypeLocale=kbd.locale,
            imeSubtypeMode="keyboard",
            imeSubtypeExtraValue="KeyboardLayoutSet=%s,AsciiCapable,EmojiCapable" % kbd.internal_name)
        with open(fn, 'w') as f:
            f.write(self._tostring(tree))
        #return ('res/xml/method.xml', self._tostring(tree))

    def save_files(self, files, base):
        fn = os.path.join(base, 'deps', 'sami-ime')
        for k, v in files:
            with open(os.path.join(fn, k), 'w') as f:
                print("Saving file '%s'..." % k)
                f.write(v)

    def get_source_tree(self, base, sdk_base):
        # TODO check SDK base is valid

        deps_dir = os.path.join(base, 'deps')
        os.makedirs(deps_dir, exist_ok=True)

        processes = []

        repos = [
            ('sami-ime', 'https://github.com/bbqsrc/sami-ime.git')
            ]

        for d, url in repos:
            cmd = ['git', 'clone', url]
            cwd = deps_dir

            if os.path.isdir(os.path.join(deps_dir, d)):
                continue

            print("Cloning repository '%s'..." % d)
            processes.append(subprocess.Popen(cmd, cwd=cwd))

        for process in processes:
            output = process.wait()
            if process.returncode != 0:
                raise Exception(output[1])

        processes = []

        for d, url in repos:
            print("Updating repository '%s'..." % d)

            cmd = """git checkout stable;
                     git reset --hard;
                     git clean -f;
                     git pull;"""
            cwd = os.path.join(deps_dir, d)

            processes.append(subprocess.Popen(cmd, cwd=cwd, shell=True))

        for process in processes:
            output = process.wait()
            if process.returncode != 0:
                raise Exception(output[1])

        print("Create Android project...")

        cmd = "%s update project -n SamiIME -t android-19 -p ." % \
            os.path.join(os.path.abspath(sdk_base), 'tools/android')
        process = subprocess.Popen(cmd, cwd=os.path.join(deps_dir, 'sami-ime'),
                shell=True)
        output = process.wait()
        if process.returncode != 0:
            raise Exception(output[1])

        #print("Updating build.xml...")

        #self.update_build_xml(base, sdk_base)

    def create_ant_properties(self):
        data = "package.name=%s\n" % self._project.target('android')['packageId']

        return ('ant.properties', data)

    #def update_build_xml(self, base, sdk_base):
    #    base_buildxml_fn = os.path.join(sdk_base, 'tools', 'ant', 'build.xml')
    #    buildxml_fn = os.path.join(base, 'deps', 'sami-ime', 'build.xml')
    #
    #    with open(base_buildxml_fn) as f:
    #        base_buildxml = etree.parse(f)
    #
    #    with open(buildxml_fn) as f:
    #        buildxml = etree.parse(f)
    #
    #    root = buildxml.getroot()
    #
    #    target = base_buildxml.xpath('target[@name="-package-resources"]')[0]
    #    SubElement(target[1][0], 'nocompress', extension='dict')
    #    root.insert(len(root)-1, target)
    #
    #    with open(buildxml_fn, 'w') as f:
    #        f.write(self._tostring(root))

    def kbd_layout_set(self, kbd):
        out = Element("KeyboardLayoutSet", nsmap={"latin": self.NS})

        kbd_str = "@xml/kbd_%s" % kbd.internal_name

        self._subelement(out, "Element", elementName="alphabet",
            elementKeyboard=kbd_str,
            enableProximityCharsCorrection="true")

        for name, kbd_str in (
            ("alphabetAutomaticShifted", kbd_str),
            ("alphabetManualShifted", kbd_str),
            ("alphabetShiftLocked", kbd_str),
            ("alphabetShiftLockShifted", kbd_str),
            ("symbols", "@xml/kbd_symbols"),
            ("symbolsShifted", "@xml/kbd_symbols_shift"),
            ("phone", "@xml/kbd_phone"),
            ("phoneSymbols", "@xml/kbd_phone_symbols"),
            ("number", "@xml/kbd_number")
        ):
            self._subelement(out, "Element", elementName=name, elementKeyboard=kbd_str)

        return self._tostring(out)

    def row_has_special_keys(self, kbd, n, style):
        for key, action in kbd.get_actions(style).items():
            if action.row == n:
                return True
        return False

    def rows(self, kbd, style):
        out = Element("merge", nsmap={"latin": self.NS})

        self._subelement(out, "include", keyboardLayout="@xml/key_styles_common")

        for n, values in enumerate(kbd.modes['default']):
            n += 1

            row = self._subelement(out, "Row")
            include = self._subelement(row, "include", keyboardLayout="@xml/rowkeys_%s%s" % (
                kbd.internal_name, n))

            if not self.row_has_special_keys(kbd, n, style):
                self._attrib(include, keyWidth='%.2f%%p' % (100 / len(values)))
            else:
                self._attrib(include, keyWidth='%.2f%%p' % self.key_width)

        # All the fun buttons!
        self._subelement(out, "include", keyboardLayout="@xml/row_qwerty4")

        return self._tostring(out)

    def gen_key_width(self, kbd, style):
        m = 0
        for row in kbd.modes['default']:
            r = len(row)
            if r > m:
               m = r

        vals = {
            "phone": 95,
            "tablet": 90
        }

        self.key_width = (vals[style] / m)

    def keyboard(self, kbd, **kwargs):
        out = Element("Keyboard", nsmap={"latin": self.NS})

        self._attrib(out, **kwargs)

        self._subelement(out, "include", keyboardLayout="@xml/rows_%s" % kbd.internal_name)

        return self._tostring(out)

    def rowkeys(self, kbd, style):
        # TODO check that lengths of both modes are the same
        for n in range(1, len(kbd.modes['default'])+1):
            merge = Element('merge', nsmap={"latin": self.NS})
            switch = self._subelement(merge, 'switch')

            case = self._subelement(switch, 'case',
                keyboardLayoutSetElement="alphabetManualShifted|alphabetShiftLocked|" +
                                         "alphabetShiftLockShifted")

            self.add_rows(kbd, n, kbd.modes['shift'][n-1], style, case)

            default = self._subelement(switch, 'default')

            self.add_rows(kbd, n, kbd.modes['default'][n-1], style, default)

            yield ('rowkeys_%s%s.xml' % (kbd.internal_name, n), self._tostring(merge))

    def _attrib(self, node, **kwargs):
        for k, v in kwargs.items():
            node.attrib["{%s}%s" % (self.NS, k)] = v

    def add_button_type(self, key, action, row, tree, is_start):
        node = self._element("Key")
        width = action.width

        if width == "fill":
            if is_start:
                width = "%.2f%%" % ((100 - (self.key_width * len(row))) / 2)
            else:
                width = "fillRight"
        elif width.endswith("%"):
            width += 'p'

        if key == "backspace":
            self._attrib(node, keyStyle="deleteKeyStyle")
        if key == "enter":
            self._attrib(node, keyStyle="enterKeyStyle")
        if key == "shift":
            self._attrib(node, keyStyle="shiftKeyStyle")
        self._attrib(node, keyWidth=width)

        tree.append(node)

    def add_special_buttons(self, kbd, n, style, row, tree, is_start):
        side = "left" if is_start else "right"

        for key, action in kbd.get_actions(style).items():
            if action.row == n and action.position in [side, 'both']:
                self.add_button_type(key, action, row, tree, is_start)

    def add_rows(self, kbd, n, values, style, out):
        i = 1

        self.add_special_buttons(kbd, n, style, values, out, True)

        for key in values:
            more_keys = kbd.get_longpress(key)

            node = self._subelement(out, "Key", keyLabel=key)
            if n == 1:
                if i > 0 and i <= 10:
                    if i == 10:
                        i = 0
                    self._attrib(node, keyHintLabel=str(i), additionalMoreKeys=str(i))
                    if i > 0:
                        i += 1
                elif more_keys is not None:
                    self._attrib(node, keyHintLabel=more_keys[0])

            elif more_keys is not None:
                self._attrib(node, moreKeys=','.join(more_keys))
                self._attrib(node, keyHintLabel=more_keys[0])

        self.add_special_buttons(kbd, n, style, values, out, False)
