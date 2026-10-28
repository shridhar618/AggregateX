// Tiny module-level signal: has the intro loader finished?
// Lets count-up animations wait until they are actually visible.
let booted = false;
const listeners = new Set();

export const markBooted = () => {
  if (booted) return;
  booted = true;
  listeners.forEach((fn) => fn());
  listeners.clear();
};

export const whenBooted = (fn) => {
  if (booted) {
    fn();
    return () => {};
  }
  listeners.add(fn);
  return () => listeners.delete(fn);
};
