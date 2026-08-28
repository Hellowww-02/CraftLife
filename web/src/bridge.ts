/** Native desktop bridge (PyQt injects window.craftlifeNative). Safe no-op in browser. */

type Native = {
  pickFile?: (accept?: string) => Promise<string | null>;
  notify?: (title: string, body: string) => void;
  openPath?: (path: string) => void;
};

function native(): Native {
  return ((window as any).craftlifeNative || {}) as Native;
}

export const bridge = {
  async pickFile(accept?: string): Promise<string | null> {
    const n = native();
    if (n.pickFile) return n.pickFile(accept);
    return null;
  },
  notify(title: string, body: string) {
    const n = native();
    if (n.notify) n.notify(title, body);
    else if ("Notification" in window && Notification.permission === "granted") {
      new Notification(title, { body });
    }
  },
};
