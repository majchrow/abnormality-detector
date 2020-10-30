import {Component} from '@angular/core';
import {HttpClient} from '@angular/common/http';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'frontend';

  constructor(
    private http: HttpClient) {
  }


  // test msg to communicate with backend
  test() {
    this.http.get(
      'http://172.18.0.1:5000/'
    ).subscribe(res => console.log(res));
  }

}
