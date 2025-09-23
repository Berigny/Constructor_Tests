(function () {
  const COMPONENT_READY = "streamlit:componentReady";
  const SET_COMPONENT_VALUE = "streamlit:setComponentValue";
  const SET_FRAME_HEIGHT = "streamlit:setFrameHeight";
  const RENDER_EVENT = "streamlit:render";
  const CUSTOM_COMPONENT_API_VERSION = 1;

  const listeners = new Map();

  function getHandlers(type) {
    if (!listeners.has(type)) {
      listeners.set(type, new Set());
    }
    return listeners.get(type);
  }

  function emit(type, detail) {
    const handlers = listeners.get(type);
    if (!handlers) {
      return;
    }
    handlers.forEach((handler) => {
      try {
        handler({ detail });
      } catch (error) {
        console.error("Streamlit component handler error", error);
      }
    });
  }

  function isFromStreamlit(event) {
    if (!event || event.source !== window.parent) {
      return false;
    }
    const data = event.data;
    return !!(data && typeof data === "object" && data.type === RENDER_EVENT);
  }

  function onMessage(event) {
    if (!isFromStreamlit(event)) {
      return;
    }
    emit(RENDER_EVENT, event.data);
  }

  function inferDataType(value) {
    if (value instanceof Uint8Array || value instanceof ArrayBuffer) {
      return "bytes";
    }
    return "json";
  }

  function normalizeValue(value) {
    if (value instanceof ArrayBuffer) {
      return Array.from(new Uint8Array(value));
    }
    if (value instanceof Uint8Array) {
      return Array.from(value);
    }
    return value;
  }

  function postToStreamlit(type, payload) {
    const parentWindow = window.parent;
    if (!parentWindow || parentWindow === window) {
      return;
    }
    parentWindow.postMessage({ type, ...payload }, "*");
  }

  const Streamlit = {
    RENDER_EVENT,
    events: {
      addEventListener(type, handler) {
        if (typeof handler !== "function") {
          return;
        }
        getHandlers(type).add(handler);
      },
      removeEventListener(type, handler) {
        const handlers = listeners.get(type);
        if (!handlers) {
          return;
        }
        handlers.delete(handler);
        if (handlers.size === 0) {
          listeners.delete(type);
        }
      },
    },
    setComponentReady() {
      postToStreamlit(COMPONENT_READY, { apiVersion: CUSTOM_COMPONENT_API_VERSION });
    },
    setFrameHeight(height) {
      const numericHeight = Number(height);
      if (!Number.isFinite(numericHeight)) {
        return;
      }
      postToStreamlit(SET_FRAME_HEIGHT, { height: numericHeight });
    },
    setComponentValue(value) {
      postToStreamlit(SET_COMPONENT_VALUE, {
        value: normalizeValue(value),
        dataType: inferDataType(value),
      });
    },
  };

  window.Streamlit = Streamlit;
  window.addEventListener("message", onMessage);
})();
