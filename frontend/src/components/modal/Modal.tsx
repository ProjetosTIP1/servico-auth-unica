import { useEffect, useRef, useState } from "react";
import styles from "./style.module.css";

type PositionTypes =
  | "top-left"
  | "top-right"
  | "bottom-left"
  | "bottom-right"
  | "center";

/** * Modal component that displays content in a modal dialog.
 * @param {boolean} isOpen - Indicates if the modal is open.
 * @param {function} onClose - Function to call when the modal should be closed.
 * @param {PositionTypes} position - Position of the modal on the screen (top-left, top-right, bottom-left, bottom-right, center).
 * @param {React.ReactNode} children - Content to display inside the modal.
 * @param {boolean} isBluer - If true, applies a blur effect to the background.
 * @returns {JSX.Element|null} - Returns the modal JSX or null if not open.
 */
export default function Modal({
  isOpen,
  onClose,
  position = "center",
  children,
  isBlur = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  position?: PositionTypes;
  children: React.ReactNode;
  isBlur?: boolean;
}) {
  const modalRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);
  const [isClosing, setIsClosing] = useState(false);

  const positionClasses = {
    "top-left": "top-4 left-4",
    "top-right": "top-4 right-4",
    "bottom-left": "bottom-4 left-4",
    "bottom-right": "bottom-4 right-4",
    center: "flex items-center justify-center",
  };
  const positionClass = positionClasses[position!] || "center";

  useEffect(() => {
    if (isOpen) {
      setIsVisible(true);
      setIsClosing(false);
      document.body.style.overflow = "hidden"; // Prevent scrolling when modal is open
    } else if (isVisible) {
      // Start closing animation
      setIsClosing(true);
      // Hide modal after animation completes
      const timer = setTimeout(() => {
        setIsVisible(false);
        setIsClosing(false);
        document.body.style.overflow = ""; // Restore scrolling when modal is closed
      }, 300); // Match animation duration

      return () => clearTimeout(timer);
    } else {
      document.body.style.overflow = ""; // Restore scrolling when modal is closed
    }
  }, [isOpen, isVisible]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        modalRef.current &&
        !modalRef.current.contains(event.target as Node)
      ) {
        onClose();
      }
    };
    if (isVisible) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isVisible, onClose]);

  if (!isVisible) return null;

  const CloseBtn = () => (
    <button
      className={styles.closeButton}
      onClick={onClose}
      aria-label="Close modal"
    >
      &times;
    </button>
  );

  return (
    <div
      className={`fixed inset-0 z-40 flex items-center justify-center ${
        isBlur ? styles.blur : ""
      }`}
    >
      <div
        ref={modalRef}
        className={`absolute z-50 ${positionClass} ${styles.modal} ${
          isClosing ? styles.hidden : ""
        }`}
      >
        <CloseBtn />
        {children}
      </div>
    </div>
  );
}
