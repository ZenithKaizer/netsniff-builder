"use strict";

/* IMPORT DES DEPENDANCES */
const jsLibPath = '/home/pptruser/.lib/netsniff-url/';
const netsniffPrototype = require(jsLibPath + 'netsniffPrototype.js');

/* Récupération des paramètres en entrée */
let conf = process.argv[2];
let filename = process.argv[3];
let thread_nb = '[Thread ID: ' + process.argv[4] + ']' ;
let browserLessURL = process.env['BROWSERLESS_URL'];

/* Execution du script */
(async() => {
    let inst = new netsniffPrototype(conf, filename, thread_nb, browserLessURL);
    await inst.createBrowser();
    await inst.loginOnSite();
    await inst.gotoUrl();
    await inst.checkHAR_genScreenshot();
    await inst.closeBrowser();
})();
