function isValidInteger(rawValue) {
    return /^-?[0-9]+$/.test(rawValue);
}

function isValidFloat(rawValue) {
    return /^-?[0-9]+(\.[0-9]+)?$/.test(rawValue);
}

function isValidCard(rawValue) {
    return /^-?[0-9a-z]+?$/.test(rawValue);
}

function isValidIdentification(rawValue) {
    return /^[0-9]{17}[0-9X]$/.test(rawValue);
}

function isValidCellphone(rawValue) {
    return /^(\+86)([0-9]{11})$/.test(rawValue);
}

function isValidCaptcha(rawValue) {
    return /^[0-9]{6}$/.test(rawValue);
}

function sendApiRequest(url, parameters, callback) {
    var body = "";
    for (var key in parameters) {
        body = body + key + "=" + encodeURIComponent(parameters[key]) + "&";
    }
    var xmlHttpRequest = (window.XMLHttpRequest) ? (new XMLHttpRequest()) : (new ActiveXObject("Microsoft.XMLHTTP"));
    xmlHttpRequest.onreadystatechange = function() {
        if (xmlHttpRequest.readyState == 4 && xmlHttpRequest.status == 200) {
            var result = JSON.parse(xmlHttpRequest.responseText);
            callback(result);
        }
    };
    xmlHttpRequest.open("post", url, true);
    xmlHttpRequest.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xmlHttpRequest.send(body);
}

function logout() {
    if (navigator.userAgent.indexOf("Safari") >= 0 || confirm("确认退出么？")) {
        document.cookie = "sessionId='';path=/;expires=" + (new Date()).toGMTString();
        window.location.reload();
    }
}
