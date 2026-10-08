/* Expose clipboard controls only when progressive enhancement is available. */
document.documentElement.classList.add('js-enabled');

/* Native controls remain available even without this enhancement. */
(() => {
  const video = document.getElementById('identity-video');
  const button = document.getElementById('identity-play');
  const status = document.getElementById('identity-status');
  if (!video || !button || !status) return;
  let played = false;
  const update = () => {
    button.textContent = video.paused ? (played ? 'Replay animation' : 'Play animation') : 'Pause animation';
  };
  button.hidden = false;
  button.addEventListener('click', async () => {
    status.textContent = '';
    if (!video.paused) {
      video.pause();
      return;
    }
    video.currentTime = 0;
    try {
      await video.play();
    } catch {
      status.textContent = 'Playback could not start. Use the native controls or download the animation.';
      update();
    }
  });
  video.addEventListener('play', () => { played = true; update(); });
  video.addEventListener('pause', update);
  video.addEventListener('ended', () => {
    video.load();
    update();
  });
  video.addEventListener('error', () => {
    status.textContent = 'Animation unavailable. View the static PNG or download the animation.';
    update();
  });
  window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', event => {
    if (event.matches) video.pause();
  });
})();
