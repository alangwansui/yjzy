# -*- coding: utf-8 -*-
import os
import shutil
import os.path
import re

BASE_DIR = os.path.dirname(__file__)

out = os.path.exists('out')
if(out):
    shutil.rmtree('out')
    os.mkdir('out')
else:
    os.mkdir('out')

_build = os.path.exists('build')
if(_build):
    shutil.rmtree('build')
    os.mkdir('build')
else:
    os.mkdir('build')

keystore = '7668c4b8-1cfa-4eee-9be3-d494c07a24e8'
keypass = 'qononw'
keyalias = '@@@@@@@@@'

BASE_DIR = os.path.dirname(__file__)

outDir = os.path.join(BASE_DIR, "out")
buildDir = os.path.join(BASE_DIR, "build")
targetDir = os.path.join(BASE_DIR, "target")
list = os.listdir(os.path.join(BASE_DIR, "target"))
for file in list:
    print("start sign: " + file)
    signedFile = os.path.join(buildDir, file + "signed.apk")
    outFile = os.path.join(outDir, file)
    f = os.path.join(targetDir, file)

    # v1签名
    signcmd = 'jarsigner -sigalg SHA1withRSA -digestalg SHA1 -keystore "%s" -storepass "%s" -signedjar "%s" "%s" "%s"' % (keystore, keypass, signedFile, f, keyalias)
    os.system(signcmd)

    # zipalign
    aligncmd = 'zipalign -f 4 "%s" "%s"' % (signedFile, outFile)
    os.system(aligncmd)

    # v2签名
    signcmd2 = 'apksigner sign --ks %s --ks-pass pass:%s --ks-key-alias %s %s' % (keystore, keypass, keyalias, outFile)
    os.system(signcmd2)

    print(file + " finish\n")
