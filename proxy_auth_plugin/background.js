
        var config = {
                mode: "fixed_servers",
                rules: {
                singleProxy: {
                    scheme: "http",
                    host: "45.135.132.196",
                    port: parseInt(45785)
                },
                bypassList: ["localhost"]
                }
            };
        
        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
        
        function callbackFn(details) {
            return {
                authCredentials: {
                    username: "Seleblinova",
                    password: "L5m8GvH"
                }
            };
        }
        
        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {urls: ["<all_urls>"]},
                    ['blocking']
        );
    