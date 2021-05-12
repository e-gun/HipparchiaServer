//
//	HipparchiaServer: an interface to a database of Greek and Latin texts
//	Copyright: E Gunderson 2016-21
//	License: License: GNU GENERAL PUBLIC LICENSE 3
//      (see LICENSE in the top level directory of the distribution)
//

//
// PROGRESS INDICATOR
//

function checkactivityviawebsocket(searchid) {
    $.getJSON('/search/confirm/'+searchid, function(portnumber) {
        let pd = $('#pollingdata');
        let ip = location.hostname;
        // but /etc/nginx/nginx.conf might have a WS proxy and not the actual WS host...
        let s = new WebSocket('ws://'+ip+':'+portnumber+'/');
        let amready = setInterval(function(){
            if (s.readyState === 1) { s.send(JSON.stringify(searchid)); clearInterval(amready); }
            }, 10);
        s.onmessage = function(e){
            let progress = JSON.parse(e.data);
            displayprogress(searchid, progress);
            // console.log(progress)
            if  (progress['active'] === 'inactive') { pd.html(''); s.close(); s = null; }
            }
    });
}

function displayprogress(searchid, progress){
    // note that morphologychartjs() has its own version of this function: changes here should be made there too
    let r = progress['Remaining'];
    let t = progress['Poolofwork'];
    let h = progress['Hitcount'];
    let pct = Math.round((t-r) / t * 100);
    let m = progress['Statusmessage'];
    let l = progress['Launchtime'];
    let x = progress['Notes'];
    let id = progress['ID'];
    let a = progress['Activity'];

    // let thehtml = '[' + id + '] ';
    let thehtml = '';

    if (id === searchid) {
        if (r !== undefined && t !== undefined && !isNaN(pct)) {
            let e = Math.round((new Date().getTime() / 1000) - l);

            if (t !== -1) {
                thehtml += m + ': <span class="progress">' + pct + '%</span> completed&nbsp;(' + e + 's)';
            } else {
                thehtml += m + '&nbsp;(' + e + 's)';
            }

            if (h > 0) {
                thehtml += '<br />(<span class="progress">' + h + '</span> found)';
            }

            thehtml += '<br />' + x;
        }
    }
   $('#pollingdata').html(thehtml);
}