"use client";

import style from "./style.module.css";

const SlideInEffect = ({
  children,
  duration = 1,
}: {
  children: React.ReactNode;
  duration: number;
}) => {
  if (duration > 2 || duration <= 0) {
    duration = 1; // Default to 1 second if no valid duration is provided
  }
  let fadeIn = null;
  switch (duration) {
    case 2:
      fadeIn = style.fade_in_2s;
      break;
    case 1:
      fadeIn = style.fade_in_1s;
      break;
    case 0.5:
      fadeIn = style.fade_in_05s;
      break;
    default:
      break;
  }

  return (
    <div className={`${fadeIn} flex flex-col w-full h-full`}>{children}</div>
  );
};

export default SlideInEffect;
