import IntroPageDemo from "./pages/IntroPageDemo";
import IntroFeatureDemo from "./pages/IntroFeatureDemo";
import IntroFlowDemo from "./pages/IntroFlowDemo";
import IntroProblemSolutionDemo from "./pages/IntroProblemSolutionDemo";
import IntroPreviewDemo from "./pages/IntroPreviewDemo";
import IntroEditorialDemo from "./pages/IntroEditorialDemo";
import IntroInteractiveDemo from "./pages/IntroInteractiveDemo";
import IntroCoachRoomDemo from "./pages/IntroCoachRoomDemo";
import DesignGallery from "./pages/DesignGallery";
import CoachingDemoPage from "./pages/CoachingDemoPage";

export default function DemoRouter() {
  if (window.location.pathname === "/demo/coaching") {
    return <CoachingDemoPage />;
  }

  if (window.location.pathname === "/demo/intro-coachroom") {
    return <IntroCoachRoomDemo />;
  }

  if (window.location.pathname === "/demo/intro") {
    return <DesignGallery />;
  }
  if (window.location.pathname === "/demo/intro-interactive") {
    return <IntroInteractiveDemo />;
  }

  if (window.location.pathname === "/demo/intro-editorial") {
    return <IntroEditorialDemo />;
  }

  if (window.location.pathname === "/demo/intro-preview") {
    return <IntroPreviewDemo />;
  }

  if (window.location.pathname === "/demo/intro-problem-solution") {
    return <IntroProblemSolutionDemo />;
  }

  if (window.location.pathname === "/demo/intro-flow") {
    return <IntroFlowDemo />;
  }

  if (window.location.pathname === "/demo/intro-feature") {
    return <IntroFeatureDemo />;
  }

  return <IntroPageDemo />;
}
