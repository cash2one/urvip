var sendApiRequest = function(url, parameters, callback) {
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
