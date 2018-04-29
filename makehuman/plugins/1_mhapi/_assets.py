#!/usr/bin/python

from .namespace import NameSpace

import getpath
import os
import sys
import re
import codecs
import shutil

class Assets(NameSpace):
    """This namespace wraps all calls that are related to reading and managing assets."""

    def __init__(self,api):
        self.api = api
        NameSpace.__init__(self)
        self.trace()

        self.assetTypes = ["material",
                           "model",
                           "clothes",
                           "hair",
                           "teeth",
                           "eyebrows",
                           "eyelashes",
                           "tongue",
                           "eyes",
                           "proxy",
                           "skin",
                           "pose",
                           "expression",
                           "rig",
                           "target",
                           "node_setups_and_blender_specific"]

        self.extensionToType = dict()
        self.extensionToType[".mhmat"] = "material"
        self.extensionToType[".mhclo"] = "proxy"
        self.extensionToType[".proxy"] = "proxy"
        self.extensionToType[".target"] = "target"
        self.extensionToType[".mhm"] = "models"

        self.typeToExtension = {'material'  :   'mhmat',
                                'models'    :   'mhm',
                                'model'     :   'mhm',
                                'clothes'   :   'mhclo',
                                'hair'      :   'mhclo',
                                'teeth'     :   'mhclo',
                                'eyebrows'  :   'mhclo',
                                'eyelashes' :   'mhclo',
                                'tongue'    :   'mhclo',
                                'eyes'      :   'mhclo',
                                'proxymeshes':  'proxy',
                                'target'    :   'target',
                                'skin'      :   'mhmat'}
        
        self.genericExtraKeys = ["tag"]
        self.genericKeys = ["name","description", "uuid"]
        self.genericCommentKeys = ["license","homepage","author"]

        self.proxyKeys = [
            "basemesh",
            "obj_file",
            "max_pole",
            "material",
            "z_depth",
            "x_scale",
            "y_scale",
            "z_scale"
        ]

        self.materialKeys = [
            "diffuseColor",
            "specularColor",
            "emissiveColor",
            "ambientColor",
            "diffuseTexture",
            "bumpmapTexture",
            "normalmapTexture",
            "displacementmapTexture",
            "specularmapTexture",
            "transparencymapTexture",
            "aomapTexture",
            "diffuseIntensity",
            "bumpMapIntensity",
            "normalMapIntensity",
            "displacementMapIntensity",
            "specularMapIntensity",
            "transparencyMapIntensity",
            "aoMapIntensity",
            "shininess",
            "opacity",
            "translucency",
            "shadeless",
            "wireframe",
            "transparent",
            "alphaToCoverage",
            "backfaceCull",
            "depthless",
            "castShadows",
            "receiveShadows",

        ] # There are also SSS settings, but I don't know if those actually works

        self.keyList = self.genericExtraKeys + self.genericCommentKeys + self.genericKeys +self.materialKeys + \
                       self.proxyKeys

        self.zDepth = {"Body": 31,
                       "Underwear and lingerie": 39,
                       "Socks and stockings": 43,
                       "Shirt and trousers": 47,
                       "Sweater": 50,
                       "Indoor jacket": 53,
                       "Shoes and boots": 57,
                       "Coat": 61,
                       "Backpack": 69
                      }

    def _parseGenericAssetInfo(self,fullPath):

        info = dict()

        fPath, ext = os.path.splitext(fullPath)
        basename = os.path.basename(fullPath)

        info["type"] = self.extensionToType[ext]
        info["absolute path"] = fullPath
        info["extension"] = ext
        info["basename"] = basename
        info["rawlines"] = []
        info["location"] = os.path.dirname(fullPath)
        info["parentdir"] = os.path.basename(info["location"])

        with codecs.open(fullPath,'r','utf8') as f:
            contents = f.readlines()
            for line in contents:
                info["rawlines"].append(re.sub(r"[\x0a\x0d]+",'',line))

        info["rawkeys"] = []
        info["rawcommentkeys"] = []

        for line in info["rawlines"]:
            m = re.match(r"^([a-zA-Z_]+)\s+(.*)$",line)
            if(m):
                info["rawkeys"].append([m.group(1),m.group(2)])
            m = re.match(r"^#\s+([a-zA-Z_]+)\s+(.*)$",line)
            if(m):
                info["rawcommentkeys"].append([m.group(1),m.group(2)])
        
        for genericExtraKeyName in self.genericExtraKeys:
            info[genericExtraKeyName] = set()
            for rawkey in info["rawkeys"]:
                rawKeyName = rawkey[0]
                rawKeyValue = rawkey[1]
                if rawKeyName == genericExtraKeyName:
                    info[genericExtraKeyName].add(rawKeyValue)

        for genericKeyName in self.genericKeys:
            info[genericKeyName] = None
            for rawkey in info["rawkeys"]:
                rawKeyName = rawkey[0]
                rawKeyValue = rawkey[1]
                if rawKeyName == genericKeyName:
                    info[genericKeyName] = rawKeyValue

        for genericCommentKeyName in self.genericCommentKeys:
            info[genericCommentKeyName] = None
            for commentKey in info["rawcommentkeys"]:
                commentKeyName = commentKey[0]
                commentKeyValue = commentKey[1]
                if commentKeyName == genericCommentKeyName:
                    info[commentKeyName] = commentKeyValue

        return info

    def _parseProxyKeys(self,assetInfo):
        for pk in self.proxyKeys:
            assetInfo[pk] = None
            for k in assetInfo["rawkeys"]:
                key = k[0]
                value = k[1]
                if key == pk:
                    assetInfo[pk] = value

    def _parseMaterialKeys(self,assetInfo):
        for pk in self.materialKeys:
            assetInfo[pk] = None
            for k in assetInfo["rawkeys"]:
                key = k[0]
                value = k[1]
                if key == pk:
                    assetInfo[pk] = value

    def _addPertinentKeyInfo(self,assetInfo):

        pertinentKeys = list(self.genericKeys)
        pertinentExtraKeys = list(self.genericExtraKeys)
        pertinentCommentKeys = list(self.genericCommentKeys)

        if assetInfo["type"] == "proxy":
            pertinentKeys.extend(self.proxyKeys)

        if assetInfo["type"] == "material":
            pertinentKeys.extend(self.materialKeys)

        assetInfo["pertinentKeys"] = pertinentKeys
        assetInfo["pertinentExtraKeys"] = pertinentExtraKeys
        assetInfo["pertinentCommentKeys"] = pertinentCommentKeys

    def assetTitleToDirName(self, assetTitle):
        normalizedTitle = assetTitle.strip()
        normalizedTitle = re.sub(r'_+', ' ', normalizedTitle)
        normalizedTitle = normalizedTitle.strip()
        normalizedTitle = re.sub(r'\s+', '_', normalizedTitle)
        normalizedTitle = re.sub(r'[*:,\[\]/\\\(\)]+', '', normalizedTitle)
        return normalizedTitle

    def getAssetTypes(self):
        """Returns a non-live list of known asset types"""
        return list(self.assetTypes)

    def getAssetLocation(self, assetTitle, assetType):
        alreadyKosher = ["clothes",
                         "hair",
                         "teeth",
                         "eyebrows",
                         "eyelashes",
                         "tongue",
                         "eyes"]

        needsPlural = ["material",
                       "model",
                       "skin",
                       "pose",
                       "expression",
                       "rig"]

        normalizedTitle = self.assetTitleToDirName(assetTitle)

        if assetType in alreadyKosher:
            root = self.api.locations.getUserDataPath(assetType)
            return os.path.join(root,normalizedTitle)

        if assetType in needsPlural:
            root = self.api.locations.getUserDataPath(assetType + "s")
            return os.path.join(root,normalizedTitle)

        if assetType == "proxy":
            return self.api.locations.getUserDataPath("proxymeshes")

        if assetType == "target":
            return self.api.locations.getUserDataPath("custom")

        if assetType == "model":
            return self.api.locations.getUserHomePath("models")

        raise ValueError("Could not convert title to location for asset with type",assetType)

        return None

    def openAssetFile(self, path, strip = False):
        """Opens an asset file and returns a hash describing it"""
        fullPath = self.api.locations.getUnicodeAbsPath(path)
        if not os.path.isfile(fullPath):
            return None
        info = self._parseGenericAssetInfo(fullPath)

        self._addPertinentKeyInfo(info)

        if info["type"] == "proxy":
            self._parseProxyKeys(info)

        if info["type"] == "material":
            self._parseMaterialKeys(info)

        thumbPath = os.path.splitext(path)[0] + ".thumb"

        if os.path.isfile(thumbPath):
            info["thumb_path"] = thumbPath
        else:
            info["thumb_path"] = None

        if strip:
            info.pop("rawlines",None)
            info.pop("rawkeys",None)
            info.pop("rawcommentkeys",None)

        return info

    def writeAssetFile(self, assetInfo, createBackup = True):
        """ This (over)writes the asset file named in the assetInfo's "absolute path" key. If createBackup is set to True, any pre-existing file will be backed up to it's former name + ".bak" """
        if not assetInfo:
            raise ValueError('Cannot use None as assetInfo')

        ap = assetInfo["absolute path"]
        bak = ap + ".bak"

        if createBackup and os.path.isfile(ap):
            shutil.copy(ap,bak)

        with codecs.open(ap,'w','utf8') as f:

            stillNeedToDumpCommentKeys = True

            writtenKeys = []
            writtenCommentKeys = []
            writtenExtraKeys = []

            remainingKeys = list(assetInfo["pertinentKeys"])
            remainingCommentKeys = list(assetInfo["pertinentCommentKeys"])
            remainingExtraKeys = list(assetInfo["pertinentExtraKeys"])

            for line in assetInfo["rawlines"]:
                allowWrite = True
                m = re.match(r"^([a-zA-Z_]+)\s+(.*)$",line)
                if m:
                    # If this is the first line without a hash sign, we want to 
                    # dump the remaining comment keys before doing anything else
                    if stillNeedToDumpCommentKeys:
                        if len(remainingCommentKeys) > 0:
                            for key in remainingCommentKeys:
                                if not assetInfo[key] is None:
                                    f.write("# " + key + " " + assetInfo[key] + "\x0a")

                        stillNeedToDumpCommentKeys = False

                    key = m.group(1)

                    if key in remainingKeys:
                        allowWrite = False
                        if not assetInfo[key] is None:
                            f.write(key + " " + assetInfo[key] + "\x0a")
                        writtenKeys.append(key)
                        remainingKeys.remove(key)

                    if key in remainingExtraKeys:
                        allowWrite = False

                        if not assetInfo[key] is None and len(assetInfo[key]) > 0 and not key in writtenExtraKeys:
                            for val in assetInfo[key]:
                                f.write(key + " " + val + "\x0a")
                        writtenExtraKeys.append(key)
                        remainingExtraKeys.remove(key)

                    if key in writtenExtraKeys:
                        allowWrite = False

                m = re.match(r"^#\s+([a-zA-Z_]+)\s+(.*)$",line)
                if m:
                    key = m.group(1)

                    if key in remainingCommentKeys:
                        allowWrite = False
                        if not assetInfo[key] is None:
                            f.write("# " + key + " " + assetInfo[key] + "\x0a")
                        writtenCommentKeys.append(key)
                        remainingCommentKeys.remove(key)

                if allowWrite:
                    f.write(line + "\x0a")

            if len(remainingKeys) > 0:
                for key in remainingKeys:
                    if not assetInfo[key] is None:
                        f.write(key + " " + assetInfo[key] + "\x0a")

            if len(remainingExtraKeys) > 0:
                for key in remainingExtraKeys:
                    if not assetInfo[key] is None and len(assetInfo[key]) > 0:
                        for val in assetInfo[key]:
                            f.write(key + " " + val + "\x0a")

        return True
