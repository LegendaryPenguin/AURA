interface AuraHomeProps {
  onLaunch: () => void;
  isExiting?: boolean;
}

export function AuraHome({ onLaunch, isExiting = false }: AuraHomeProps) {
  return (
    <section className={`aura-home-screen ${isExiting ? "exiting" : ""}`}>
      <div className="aura-home-topbar">
        <button type="button" className="aura-icon-btn" aria-label="Open menu" disabled>
          <span className="line-1" />
          <span className="line-2" />
          <span className="line-3" />
        </button>
        <div className="aura-home-title">ChatGPT</div>
        <button type="button" className="aura-launch-btn" onClick={onLaunch}>
          AURA
        </button>
      </div>

      <div className="aura-home-empty" />

      <div className="aura-home-suggestions" aria-hidden="true">
        <div className="aura-suggest-chip">
          <span className="aura-suggest-title">Create a cartoon</span>
          <span className="aura-suggest-sub">illustration of my pet</span>
        </div>
        <div className="aura-suggest-chip">
          <span className="aura-suggest-title">Write a thank-you note</span>
          <span className="aura-suggest-sub">to my interviewer</span>
        </div>
      </div>

      <div className="aura-home-inputbar">
        <button type="button" className="aura-circle-btn" aria-label="Add attachment" disabled>
          +
        </button>
        <div className="aura-input-pill">
          <span className="aura-input-placeholder">Ask ChatGPT</span>
        </div>
        <button type="button" className="aura-mic-btn" aria-label="Voice input" disabled>
          <span />
        </button>
      </div>
    </section>
  );
}

