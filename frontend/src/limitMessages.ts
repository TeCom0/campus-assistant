import { noticeLanguage, type NoticeLanguage } from "./privacyNotice";
import { MAX_QUESTION_CHARS } from "./requestLimits";

// The composer's counter and the message for a refused request, in the browser's
// language, as with the privacy notice: a refused question gets no language
// detection on the server, and an over-long one is never sent at all.
const TEXT: Record<
  NoticeLanguage,
  { tooLong: string; rejectedTitle: string; rejectedMessage: string }
> = {
  en: {
    tooLong: "Too long: shorten your question to send it.",
    rejectedTitle: "This question couldn't be sent",
    rejectedMessage:
      "The server refused it because it's too long or holds characters it doesn't accept. Edit it and try again.",
  },
  // French puts a no-break space before a colon, so the colon can't start a line.
  fr: {
    tooLong: "Trop longue : raccourcissez votre question pour l'envoyer.",
    rejectedTitle: "Cette question n'a pas pu être envoyée",
    rejectedMessage:
      "Le serveur l'a refusée : elle est trop longue ou contient des caractères non acceptés. Modifiez-la et réessayez.",
  },
};

export function limitMessages(browserLanguage: string) {
  const language = noticeLanguage(browserLanguage);
  const number = new Intl.NumberFormat(language);
  return {
    language,
    ...TEXT[language],
    counter: (count: number) => `${number.format(count)} / ${number.format(MAX_QUESTION_CHARS)}`,
  };
}
