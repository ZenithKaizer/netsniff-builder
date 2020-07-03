"use strict";

const YAML = require("yaml");
const fs = require("fs");

module.exports = {
  loadConfiguration: function(configuration) {
    let data = new Buffer(configuration, "base64");
    let conf = data.toString("ascii");
    conf = YAML.parse(conf);
    return conf;
  },

  passwordReader: function(passEnv) {
    let passwordResult = undefined;
    if (passEnv.match(/^\$/)) {
      passEnv = passEnv.replace(/\$/, "");
      passwordResult = process.env[passEnv];
    }
    return passwordResult;
  },

  setViewport: function(page, conf) {
    let viewPort = {
      width: 800,
      height: 600
    };
    if (conf["page_viewport"] != undefined) {
      viewPort.width = conf["page_viewport"]["width"];
      viewPort.height = conf["page_viewport"]["height"];
    }
    page.setViewport(viewPort);
  },

  setHeaders: function(page, conf) {
    if (conf["request_headers"] != undefined) {
      page.setExtraHTTPHeaders(conf["request_headers"]);
    }
  },

  setCookies: function(page, conf) {
    if (conf["request_cookies"] != undefined) {
      page.setCookie(...conf["request_cookies"]);
    }
  },

  setUserAgent: function(page, conf) {
    let user_agent =
      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/77.0.3835.0 Safari/537.36 Hebex/netsniff";
    if (conf["request_user_agent"] != undefined) {
      user_agent = conf["request_user_agent"];
    }
    page.setUserAgent(user_agent);
  },

  waitForResponse: function(page, wait_for_response) {
    if (wait_for_response) {
      page.waitForResponse(
        response => response.url().match(wait_for_response["match"]),
        {
          timeout: wait_for_response["timeout"]
        }
      );
    }
  },

  clearHarScreenshot: function(arrFilename) {
    arrFilename.forEach(filename => {
      if (fs.existsSync(filename)) {
        fs.unlinkSync(filename);
      }
    });
  }
};
