export class Meeting {
  constructor(title: string, content: Array<string>) {
    this.title = title;
    this.content = content;
  }

  title: string;
  content: Array<string>;

  config: Map<string, boolean> = new Map([
    ['recording allowed', true],
    ['streaming allowed', true],
    ['one active speaker', false]
  ]);


}
