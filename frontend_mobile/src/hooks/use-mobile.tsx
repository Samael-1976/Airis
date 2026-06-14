import * as React from "react";

const MOBILE_BREAKPOINT = 1280;
const TABLET_BREAKPOINT = 1280; // [NUOVO] Per Protocollo BB

export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined);

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    };
    mql.addEventListener("change", onChange);
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return !!isMobile;
}

// --- [NUOVO] EXPORT PER PROTOCOLLO BB (MOBILE FIRST) ---
export function useIsPortrait() {
  const checkIsPortrait = () => {
    if (typeof window === "undefined") return false;
    const isOrientationPortrait = window.matchMedia("(orientation: portrait)").matches;
    const isSmallScreen = window.innerWidth < TABLET_BREAKPOINT;
    return isOrientationPortrait || isSmallScreen;
  };

  const [isPortrait, setIsPortrait] = React.useState<boolean>(checkIsPortrait());

  React.useEffect(() => {
    const handleResize = () => {
      setIsPortrait(checkIsPortrait());
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("orientationchange", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("orientationchange", handleResize);
    };
  }, []);

  return isPortrait;
}