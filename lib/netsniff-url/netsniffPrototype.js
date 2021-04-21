"use strict";

/* IMPORT DES DEPENDANCES */
const fs = require('fs');
const sleep = require('util').promisify(setTimeout);

const {
    promisify
} = require('util');


const jsLibPath = '/home/pptruser/.lib/netsniff-url/';
const resultPath = '/home/pptruser/attachments/';
const chromeExecutable = '/usr/bin/google-chrome';

const puppeteer = require('puppeteer');
const puppeteerHar = require('puppeteer-har');
const utils = require(jsLibPath + 'utils');
const validate = require('har-validator');
const log4js = require('log4js');

var har = require('./generate_har.js');

/* PROTOTYPE netsniff */
function netsniffPrototype(config, filename, threadId, browserLessURL) {
    this.config = utils.loadConfiguration(config);
    this.threadId = threadId;
    this.filename = filename;
    this.browserLessURL = browserLessURL;
    this.harFilename = resultPath + this.filename + '.har';

    // Variables pour puppeteer
    this.browser;
    this.context;
    this.page;
    this.har;

    // Initialisation des logs
    log4js.configure({
        appenders: {
            console: {
                type: 'console',
                layout: {
                    type: 'pattern',
                    pattern: '%d{yyyy-MM-dd:hh:mm:ss,SSS} %[%p%] [%f{1}:%l] %m',
                }
            }
        },
        categories: { default: { appenders: [ 'console' ], level: 'info', enableCallStack: true } }
    });
    this.logger = log4js.getLogger('console');

    // Initialisation et ouverture du navigateur
    this.createBrowser = async function() {
        // Création du browser
        if (this.browser === undefined || !this.browser.isConnected()) {
            await puppeteer.connect({
                executablePath: chromeExecutable,
                ignoreDefaultArgs: true,
                browserWSEndpoint: browserLessURL
            }).then(ret => {
                this.browser = ret;
                this.logger.info(this.threadId + ' Browser connected');

                // print user_agent
//                let user_ag = this.browser.userAgent();
//                user_ag.then(ret => {
//                    this.logger.debug(this.threadId + ' user-agent : ' + val);
//                });
//                this.logger.debug(this.threadId + ' user-agent : ' + user_ag);

                // print pid process
//                let pid = this.browser.process();
//                this.logger.debug(this.threadId + ' browser process pid : ' + pid);

                // print WSEndpoint
//                let wsendpoint = this.browser.wsEndpoint();
//                this.logger.debug(this.threadId + 'WSEndpoint : ' + wsendpoint);
            }).catch((e) => {
                this.logger.fatal(this.threadId + " Browser could not be created " + e.stack);
                process.exit(1);
            });
        }

        // Création du context et passage en navigation privée
        if (this.context === undefined || !this.context.isIncognito()) {
            this.context = await this.browser.createIncognitoBrowserContext().catch(() => {
                this.logger.error(this.threadId + " Cannot set incognito context " + e.stack);
                this.context = this.browser.defaultBrowserContext();
            });
            this.logger.info(this.threadId + ' Context opened');
        }

        // Ouverture du navigateur
        if (this.page === undefined || this.page.isClosed()) {
            await this.context.newPage()
                .then(ret => {
                    this.page = ret;
                    this.logger.info(this.threadId + ' Page opened');

                    // print browser version
//                    let brws_version = this.page.browser().version();
//                    this.logger.debug(this.threadId + ' browser version : ' + brws_version);
                }).catch(() => {
                    this.logger.fatal(this.threadId + " Cannot set page " + e.stack);
                    this.closeBrowser();
                    process.exit(1);
                });
        }

        // Application d'options cache et Timeout
        //await this.page.setCacheEnabled([false]);
        //await this.page.setDefaultTimeout(1000 * 120);
    };

    // Tentative de connexion utilisateur sur le site
    this.loginOnSite = async function() {
        if (typeof this.config['identity'] !== undefined) {
            await utils.setHeaders(this.page, this.config);
            await utils.setUserAgent(this.page, this.config);
            let url = this.config['identity']['url'];
            let username = this.config['identity']['username'];
            let password = utils.passwordReader(this.config['identity']['password']);

            this.logger.info(this.threadId + ' Trying to login to ' + url);

            await this.page.setViewport({ width: 1024, height: 768 });
            //await this.page.setCacheEnabled(false);
            await this.page.goto(url, {waitUntil: 'load', timeout: 120000})
                .catch((e) => {
                    this.closeBrowser();
                    let exit_code = 9;
                    this.logger.error(this.threadId + ' Process exitLoginPageError event page cannot load login url ' + exit_code + ' ' + e.stack);
                    process.exit(exit_code);

    });

            // Saisie du login dans le formulaire
            try {
                let cssSelectorLogin = '#login';
                await this.page.mainFrame().waitForSelector(cssSelectorLogin, {timeout: 20000});
                this.logger.debug(this.threadId + ' Typing email...');
                await this.page.type(cssSelectorLogin, username);
            } catch (e) {
                this.closeBrowser();
                let exit_code = 9;
                this.logger.error(this.threadId + " Process exitLoginPageError event username's field not found " + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            }

            // Validation du login dans le formulaire
            let cssSelectorButton = '#btnSubmit';
            try {
                await this.page.mainFrame().waitForSelector(cssSelectorButton, {timeout: 20000});
                this.logger.debug(this.threadId + ' Clicking next button...');
                await this.page.click(cssSelectorButton);
            } catch (e) {
                this.closeBrowser();
                let exit_code = 9;
                this.logger.error(this.threadId + " Process exitLoginPageError event button to validate login not found " + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            }

            // Saisie du mot de passe dans le formulaire
            try {
                let cssSelectorPasswd = '#password';
                this.logger.debug(this.threadId + ' Waiting for password field...');
                await this.page.mainFrame().waitForSelector(cssSelectorPasswd, { visible: true, timeout: 20000 });
                this.logger.debug(this.threadId + ' Typing password...');
                await this.page.type(cssSelectorPasswd, password, { delay: 100 });
            } catch (e) {
                this.closeBrowser();
                let exit_code = 9;
                this.logger.error(this.threadId + " Process exitLoginPageError event password's field not found " + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            }

            // Validation du mot de passe dans le formulaire
            this.logger.debug(this.threadId + ' Clicking sign in button...');
            await this.page.click(cssSelectorButton, { delay: 100 }).catch(() => {
                this.closeBrowser();
                let exit_code = 9;
                this.logger.error(this.threadId + ' Process exitLoginPageError event with code: ' + exit_code);
                this.logger.error(this.threadId + " Process exitLoginPageError event button to validate password not found " + exit_code);
                process.exit(exit_code);
            });

            // Récupération du retour de la page
            try {
                let response = await this.page.waitForRequest(request => request.url() === 'https://www.orange.fr/portail' && request.method() === 'GET');
                //let response_json = await response.json();
                return response.url();
                //console.log(response.url();

                // Vérification de l'authentification
                //if ('return_url' in response) {
                //    this.logger.info(this.threadId + ' Logging successful');
                //    return true;
                //} else {
                //    this.logger.error(this.threadId + ' Logging failed : ' + response_json['message']);
                //    return false;
                //}

                //this.logger.info(this.threadId + ' Logging successful');


                this.logger.info(this.threadId + ' Logging successful');
            } catch (e) {
                this.closeBrowser();
                let exit_code = 9;
                this.logger.error(this.threadId + ' Process exitLoginPageError event the login response is empty ' + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            }
        }
    }

    // Démarrage d'un HAR
    this.harStart = async function() {
        await har.register_events(this.page)
            .then(() => this.logger.info(this.threadId + ' HAR started'))
            .catch((e) => {
                this.closeBrowser();
                let exit_code = 5;
                this.logger.error(this.threadId + ' Process exitHarStartError event Har detection error ' + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            });
    }

    // Arrêt d'un HAR
    this.harStop = async function() {
        const har_results = await har.get_har();
        await promisify(fs.writeFile)(resultPath + this.filename + '.har', JSON.stringify(har_results))
            .then(() => this.logger.info(this.threadId + ' HAR stopped'))
            .catch((e) => {
                this.closeBrowser();
                let exit_code = 8;
                this.logger.error(this.threadId + ' Process exitHarNotStopped event Har not stopped properly ' + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            });
    }


    // Aller sur une page d'un site
    this.gotoUrl = async function() {
        // Initialisation des options de la page navigateur
        await utils.setViewport(this.page, this.config);
        await utils.setCookies(this.page, this.config);
        await utils.setHeaders(this.page, this.config);
        await utils.setUserAgent(this.page, this.config);
        await this.page.setCacheEnabled([false]);

        // Navigation vers une URL

        let url = this.config['urls'];
        //this.page.on('load', () => this.logger.info(this.threadId + ' Page loaded!'));
        this.logger.info(this.threadId + ' Trying to connect to ' + url)
        await this.page.goto(url, {waitUntil: 'load', timeout: 0})
            .then(() => this.logger.info(this.threadId + ' Connected on : ' + url))
            .catch((e) => {
                //this.harStop();
                this.closeBrowser();
                let exit_code = 2;
                this.logger.error(this.threadId + ' Process exitURLError event URL detection error ' + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            });

        // Gestion du cookie concent
        if (typeof this.config['hasConsentButton'] !== undefined && this.config['hasConsentButton'] == 'true') {
            this.logger.debug(this.threadId + ' Clicking didomi-button');
            let cssSelectorDidomi = '#didomi-notice-agree-button';
            try {
                let cookieAcceptBtn = await this.page.waitForSelector(cssSelectorDidomi, { timeout: 20000, visible: true });
                this.logger.info(this.threadId + ' Didomi-button found');
                await cookieAcceptBtn.click();
                this.logger.info(this.threadId + ' Didomi-button has been clicked');
            } catch (e) {
                this.closeBrowser();
                let exit_code = 3;
                this.logger.error(this.threadId + ' Process exitHeaderTimeout event cookieAcceptBtn detection timeout ' + exit_code + ' ' + e.stack);
                process.exit(exit_code);
            }

            // Rechargement de la page
            const tic = Date.now();

            //await this.page.waitFor(15000)
            try {
                await this.harStart(this.page);
                this.logger.info(this.threadId + ' Reload Page');
                await this.page.reload({ waitUntil: "load", timeout: 0});
                this.logger.info(this.threadId + ' Page reloaded');
                this.logger.info(`${this.threadId} Second page load took: ${Date.now() - tic}ms`);
                this.logger.info(this.threadId + ' Wait for 15sec until events');
                await this.page.waitFor(15000)
            } catch (e) {
                    this.closeBrowser();
                    let exit_code = 6;
                    this.logger.error(this.threadId + ' Process exitReloadError event Reload page error ' + exit_code + ' ' + e.stack);
                    process.exit(exit_code);
            }
        }

        // Arrêt du monitoring HAR
        await this.harStop()
    }


    // Verification HAR et génération des screenshots
    this.checkHAR_genScreenshot = async function() {


        // Vérification - HAR est-il valide
        let listFilename = [
            this.harFilename,
            resultPath + this.filename + '_viewport.png',
            resultPath + this.filename + '_fullpage.png'
        ];

        if (!fs.existsSync(listFilename[0])) {
            this.logger.error(this.threadId + ' HAR File not found');
            return false;
        }

        let rawdata = fs.readFileSync(listFilename[0]);
        let harObj = JSON.parse(rawdata);

    // Validate HAR - https://github.com/ahmadnassri/node-har-validator/blob/HEAD/docs/promise.md
          validate.har(harObj)
            .then((harObj) => {
                this.logger.info(this.threadId + ' HAR structure is valid ');
            }).catch((e) => {
                this.logger.error(this.threadId + ' Not valid HAR structure ' + e.stack);
                utils.clearHarScreenshot(listFilename);
                let exit_code = 10;
                //return false;
                this.closeBrowser();
                process.exit(exit_code);
        });

        validate.cache(harObj)
            .then((harObj) => {
                    this.logger.info(this.threadId + ' HAR cache is valid ');
            }).catch((e) => {
                this.logger.error(this.threadId + ' Not valid HAR cache ' + e.stack);
                utils.clearHarScreenshot(listFilename);
                let exit_code = 10;
                this.closeBrowser();
                process.exit(exit_code);
        });

        validate.pageTimings(harObj)
            .then((harObj) => {
                    this.logger.info(this.threadId + ' HAR pageTimings is valid');
            }).catch((e) => {
                this.logger.error(this.threadId + ' Not valid HAR pageTimings ' + e.stack);
                utils.clearHarScreenshot(listFilename);
                let exit_code = 10;
                this.closeBrowser();
                process.exit(exit_code);
        });

        // Screenshots de la page affichée (viewport)
        await this.page.screenshot({path: listFilename[1], fullPage: false})
            .then(() => this.logger.info(this.threadId + ' Screenshots created - ' + listFilename[1]))
            .catch((e) => {
                this.logger.error(this.threadId + " Screenshot Viewport is not created " + e.stack);
                utils.clearHarScreenshot(listFilename);
                return false;
            });

        // Screenshots de la page affichée (fullpage)
        await this.page.screenshot({path: listFilename[2], fullPage: true})
            .then(() => this.logger.info(this.threadId + ' Screenshots created - ' + listFilename[2]))
            .catch((e) => {
                this.logger.error(this.threadId + " Screenshot Fullpage is not created " + e.stack);
                utils.clearHarScreenshot(listFilename);
                return false;
            });
    }

    // Fermeture du navigateur
    this.closeBrowser = async function() {
        await this.browser.close()
            .then(() => {
                this.logger.info(this.threadId + ' Browser closed');
                this.logger.info(this.threadId + ' Bye bye');
            }).catch((e) => this.logger.error(this.threadId + " Browser already closed " + e.stack));
    }
}

module.exports = netsniffPrototype;
