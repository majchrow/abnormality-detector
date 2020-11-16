export class Meeting {
  constructor(id: number, name: string) {
    this.id = id;
    this.name = name;
  }

  id: number;
  name: string;
  content: string[] = [];
  config: Map<string, any> = new Map();
}
