(function(){
  var s = document.createElement('script');
  s.src = 'https://cdn.socket.io/4.8.1/socket.io.min.js';
  s.onload = function(){ console.log('socket.io loaded'); };
  s.onerror = function(){ console.warn('socket.io CDN failed to load. If offline, please download socket.io client'); };
  document.head.appendChild(s);
})();
