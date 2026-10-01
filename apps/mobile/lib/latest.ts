// "Latest request wins": each call to the returned function starts a new request and hands
// back an `isLatest` check. A slower, older response (e.g. from a previous pull-to-refresh)
// must not overwrite newer data, nor switch the refresh spinner off early.
export function createLatestGuard(): () => () => boolean {
  let n = 0;
  return () => {
    const id = ++n;
    return () => id === n;
  };
}
