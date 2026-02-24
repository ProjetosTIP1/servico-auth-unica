import React from "react";
import logo_img from "@/assets/logos/p1-logo-small.png";
import "./style.module.css";

// Type definition for component props (following Interface Segregation Principle)
interface LoaderProps {
  /** Optional message to display below the loader */
  message?: string;
  /** Optional custom size for the logo */
  size?: number;
  /** Optional overlay opacity (0-1) */
  overlayOpacity?: number;
}

/**
 * Loader Component
 *
 * A full-screen loading overlay with animated logo.
 * Follows Clean Architecture principles:
 * - Single Responsibility: Only handles loading UI
 * - Open/Closed: Easy to extend with props
 * - Dependency Inversion: Depends on abstractions (props) not concrete values
 */
export default function Loader({
  message,
  size = 100,
  overlayOpacity = 0.8,
}: LoaderProps): React.ReactElement {
  // Inline styles for dynamic values (following Open/Closed Principle)
  const dynamicStyles: React.CSSProperties = {
    backgroundColor: `rgba(255, 255, 255, ${overlayOpacity})`,
  };

  const logoStyles: React.CSSProperties = {
    width: `${size}px`,
  };

  return (
    <div
      className="loadingContainer"
      style={dynamicStyles}
      role="progressbar"
      aria-label="Loading content"
    >
      <div className="loaderContent">
        <img
          className="loadingLogo"
          src={logo_img}
          alt="Company logo"
          style={logoStyles}
        />
        {message && <p className="loadingMessage">{message}</p>}
      </div>
    </div>
  );
}
