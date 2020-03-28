//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-20
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)
//

//
// PROGRESS INDICATOR
//

function checkactivityviawebsocket(searchid) {
    $.getJSON('/confirm/'+searchid, function(portnumber) {
        let pd = $('#pollingdata');
        let ip = location.hostname;
        // but /etc/nginx/nginx.conf might have a WS proxy and not the actual WS host...
        let s = new WebSocket('ws://'+ip+':'+portnumber+'/');
        let amready = setInterval(function(){
            if (s.readyState === 1) { s.send(JSON.stringify(searchid)); clearInterval(amready); }
            }, 10);
        s.onmessage = function(e){
            let progress = JSON.parse(e.data);
            displayprogress(progress);
            if  (progress['active'] === 'inactive') { pd.html(''); s.close(); s = null; }
            }
    });
}

function displayprogress(progress){
    let r = progress['remaining'];
    let t = progress['total'];
    let h = progress['hits'];
    let pct = Math.round((t-r) / t * 100);
    let m = progress['message'];
    let e = progress['elapsed'];
    let x = progress['extrainfo'];

    let thehtml = '';

    if (t !== -1) {
        thehtml += m + ': <span class="progress">' + pct + '%</span> completed&nbsp;(' + e + 's)';
    } else {
        thehtml += m + '&nbsp;(' + e + 's)';
        }

   if ( h > 0) { thehtml += '<br />(<span class="progress">' + h + '</span> found)'; }

   thehtml += '<br />' + x;

   $('#pollingdata').html(thehtml);
}